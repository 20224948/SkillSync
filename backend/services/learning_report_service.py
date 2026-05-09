from __future__ import annotations

from datetime import UTC, datetime

from ai.provider_factory import get_ai_provider
from config import get_settings
from mastery.mastery_model import calculate_mastery_report, mastery_report_to_dict
from moodle.client import MoodleClient
from moodle.evidence_mapper import (
    build_ai_criterion_mapping_from_moodle,
    build_student_rubric_evidence,
    student_rubric_evidence_to_dicts,
)
from moodle.normalisers.ai_input_builder import build_assignment_ai_input
from moodle.normalisers.assignment_normaliser import build_student_assignment_context
from moodle.normalisers.mastery_input_builder import (
    build_mastery_inputs_from_assignment_ai_input,
    build_mastery_inputs_from_quiz_contexts,
    merge_mastery_input_bundles,
)
from moodle.normalisers.quiz_normaliser import build_student_course_quiz_contexts
from moodle.services.assignments import get_assignments_by_course
from moodle.services.quizzes import get_quizzes_by_course


def _now_iso() -> str:
    """
    Returns an ISO timestamp suitable for database storage and JSON output.
    """

    return datetime.now(UTC).isoformat()


def _get_ai_model_name() -> str:
    """
    Records which model produced the AI feedback.
    """

    settings = get_settings()

    if settings.ai_provider == "gemini":
        return settings.gemini_model

    if settings.ai_provider == "ollama":
        return settings.ollama_model

    return "unknown"


def build_report_key(
    student_user_id: int,
    course_id: int,
    assignment_id: int,
) -> str:
    """
    Creates a stable key for the latest report for one student/assignment.

    Supabase uses this as an upsert key so rerunning the script updates the
    latest report instead of creating confusing duplicates during testing.
    """

    return (
        f"moodle:course:{course_id}:assignment:{assignment_id}:"
        f"student:{student_user_id}"
    )


def build_course_profile_key(
    student_user_id: int,
    course_id: int,
) -> str:
    """
    Creates a stable key for the latest course-level learning profile.
    """

    return f"moodle:course:{course_id}:student:{student_user_id}"


def _build_calculated_weak_areas(mastery_report: dict) -> list[dict]:
    """
    Converts mastery-engine weak SILOs into a compact AI/frontend list.
    """

    weak_areas = []

    for silo in mastery_report.get("weakest_silos", []):
        weak_areas.append(
            {
                "competency_id": silo.get("silo_id"),
                "title": silo.get("title"),
                "description": silo.get("description"),
                "mastery_score": silo.get("mastery_score"),
                "confidence": silo.get("confidence"),
                "evidence_count": silo.get("evidence_count"),
                "reason": "Lowest calculated mastery score below the weak-area threshold.",
                "evidence": silo.get("evidence", []),
            }
        )

    return weak_areas


def _build_ai_learning_support_input(
    assignment_ai_input: dict,
    mastery_report: dict,
    calculated_weak_areas: list[dict],
) -> dict:
    """
    Builds the payload sent to the LLM.

    The LLM receives the calculated mastery report and weak areas. It can explain
    them and generate support, but it must not calculate or change scores.
    """

    return {
        "request_type": "generate_learning_support_report",
        "student": assignment_ai_input["student"],
        "course": assignment_ai_input["course"],
        "assessment": assignment_ai_input["assessment"],
        "performance": assignment_ai_input["performance"],
        "teacher_feedback": assignment_ai_input["teacher_feedback"],
        "calculated_mastery_result": mastery_report,
        "calculated_weak_areas": calculated_weak_areas,
        "evidence_used": assignment_ai_input["rubric_evidence"],
        "ai_rules": [
            "Do not invent or modify mastery scores.",
            "Do not infer rubric-to-competency mappings.",
            "Only explain weak areas supported by calculated_weak_areas or evidence_used.",
            "Link study plan items, MCQs, and recommendations back to the provided evidence.",
        ],
    }


def _normalise_id(value: object) -> str:
    """
    Converts external IDs into stable strings.
    """

    return str(value).strip()


def _safe_float(value: object) -> float | None:
    """
    Safely converts numeric configuration values into floats.
    """

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_assignment_ids(
    client: MoodleClient,
    course_id: int,
    assignment_ids: list[int] | None,
) -> list[int]:
    """
    Resolves selected assignment IDs, defaulting to all course assignments.
    """

    if assignment_ids is not None:
        return assignment_ids

    assignments_response = get_assignments_by_course(
        client=client,
        course_id=course_id,
    )

    resolved_ids = []

    for course in assignments_response.get("courses", []):
        for assignment in course.get("assignments", []):
            assignment_id = assignment.get("id")

            if assignment_id is not None:
                resolved_ids.append(int(assignment_id))

    return resolved_ids


def _resolve_quiz_ids(
    client: MoodleClient,
    course_id: int,
    quiz_ids: list[int] | None,
) -> list[int]:
    """
    Resolves selected quiz IDs, defaulting to all course quizzes.
    """

    if quiz_ids is not None:
        return quiz_ids

    quizzes_response = get_quizzes_by_course(
        client=client,
        course_id=course_id,
    )

    return [
        int(quiz["id"])
        for quiz in quizzes_response.get("quizzes", [])
        if quiz.get("id") is not None
    ]


def _lookup_assessment_weight(
    assessment_weights: dict | None,
    source_type: str,
    assessment_id: int | str,
) -> float | None:
    """
    Looks up optional assignment/quiz weights from flexible backend payloads.
    """

    if not assessment_weights:
        return None

    assessment_id_text = _normalise_id(assessment_id)
    source_key = "assignments" if source_type == "assignment" else "quizzes"
    prefixed_key = f"{source_type}:{assessment_id_text}"

    candidates = [
        assessment_weights.get(prefixed_key),
        assessment_weights.get(assessment_id_text),
    ]

    nested_weights = assessment_weights.get(source_key)

    if isinstance(nested_weights, dict):
        candidates.append(nested_weights.get(assessment_id_text))

    for candidate in candidates:
        weight = _safe_float(candidate)

        if weight is not None:
            return weight

    return None


def _build_assignment_profile_item(
    client: MoodleClient,
    student_user_id: int,
    course_id: int,
    assignment_id: int,
    student_name: str | None,
    course_name: str | None,
    explicit_mappings: dict | list | None,
) -> dict:
    """
    Builds assignment evidence for the course-level profile.
    """

    assignment_context = build_student_assignment_context(
        client=client,
        student_user_id=student_user_id,
        course_id=course_id,
        assignment_id=assignment_id,
    )

    criterion_mapping = build_ai_criterion_mapping_from_moodle(
        client=client,
        course_module_id=assignment_context["course_module_id"],
        assignment_id=assignment_id,
        explicit_mappings=explicit_mappings,
    )

    student_competency_evidence = build_student_rubric_evidence(
        student_id=student_user_id,
        assignment_id=assignment_id,
        rubric_fillings=assignment_context.get("rubric", {}).get("rubric_fillings", []),
        criterion_mapping=criterion_mapping,
    )

    assignment_ai_input = build_assignment_ai_input(
        assignment_context=assignment_context,
        student_name=student_name,
        course_name=course_name,
        criterion_mapping=criterion_mapping,
    )

    return {
        "assignment_id": assignment_id,
        "assignment_context": assignment_context,
        "assignment_ai_input": assignment_ai_input,
        "criterion_mapping": criterion_mapping,
        "student_competency_evidence": student_competency_evidence,
    }


def _assignment_item_has_mastery_evidence(item: dict) -> bool:
    """
    Checks whether assignment evidence can contribute to mastery.
    """

    return bool(item.get("student_competency_evidence"))


def _build_assignment_student_evidence_rows(item: dict) -> list[dict]:
    """
    Converts assignment rubric evidence into generic student evidence rows.
    """

    rows = []
    assignment_context = item.get("assignment_context", {})
    assignment_ai_input = item.get("assignment_ai_input", {})

    evidence_by_criterion = {
        str(evidence.get("criterion_id")): evidence
        for evidence in assignment_ai_input.get("rubric_evidence", [])
    }

    for evidence_item in student_rubric_evidence_to_dicts(
        item.get("student_competency_evidence", [])
    ):
        criterion_id = str(evidence_item.get("criterion_id"))
        enriched_evidence = evidence_by_criterion.get(criterion_id, {})

        rows.append(
            {
                "source_type": "assignment_rubric",
                "assignment_moodle_id": str(evidence_item.get("assignment_id")),
                "criterion_id": criterion_id,
                "course_module_id": str(assignment_context.get("course_module_id")),
                "competency_id": evidence_item.get("competency_id"),
                "competency_code": enriched_evidence.get("competency_code"),
                "competency_name": enriched_evidence.get("competency_name"),
                "score": evidence_item.get("score"),
                "max_score": evidence_item.get("max_score"),
                "normalised_score": evidence_item.get("normalised_score"),
                "feedback": evidence_item.get("feedback"),
                "mapping_source": evidence_item.get("mapping_source"),
                "evidence": enriched_evidence,
            }
        )

    return rows


def _build_quiz_student_evidence_rows(quiz_contexts: list[dict]) -> list[dict]:
    """
    Converts quiz grade evidence into generic student evidence rows.
    """

    rows = []

    for context in quiz_contexts:
        if not context.get("is_valid_for_mastery"):
            continue

        selected_attempt = context.get("selected_attempt") or {}
        best_grade = context.get("best_grade") or {}

        for mapping in context.get("competency_mappings", []):
            rows.append(
                {
                    "source_type": "quiz_grade",
                    "quiz_moodle_id": str(context.get("quiz_id")),
                    "quiz_attempt_id": (
                        str(selected_attempt.get("attempt_id"))
                        if selected_attempt.get("attempt_id") is not None
                        else None
                    ),
                    "course_module_id": str(context.get("course_module_id")),
                    "competency_id": mapping.get("competency_id"),
                    "competency_code": mapping.get("competency_code"),
                    "competency_name": mapping.get("competency_name"),
                    "score": best_grade.get("grade"),
                    "max_score": best_grade.get("max_grade"),
                    "normalised_score": best_grade.get("grade_percent"),
                    "feedback": None,
                    "mapping_source": mapping.get("mapping_source"),
                    "evidence": {
                        "quiz_id": context.get("quiz_id"),
                        "quiz_name": context.get("quiz_name"),
                        "course_module_id": context.get("course_module_id"),
                        "selected_attempt": selected_attempt,
                        "best_grade": best_grade,
                        "coverage_weight": mapping.get("coverage_weight"),
                    },
                }
            )

    return rows


def _build_included_assessments(
    assignment_items: list[dict],
    quiz_contexts: list[dict],
    assignment_weights: dict[str, float],
    quiz_weights: dict[str, float],
    skipped_assessments: list[dict],
) -> list[dict]:
    """
    Builds audit metadata for the evidence sources considered by the profile.
    """

    included = []

    for item in assignment_items:
        assignment_ai_input = item.get("assignment_ai_input", {})
        assessment = assignment_ai_input.get("assessment", {})
        assignment_id = _normalise_id(item.get("assignment_id"))

        included.append(
            {
                "source_type": "assignment_rubric",
                "assignment_moodle_id": assignment_id,
                "course_module_id": assessment.get("course_module_id"),
                "name": assessment.get("name"),
                "weight_percent": assignment_weights.get(assignment_id),
                "evidence_count": len(item.get("student_competency_evidence", [])),
                "status": "included",
            }
        )

    for context in quiz_contexts:
        quiz_id = _normalise_id(context.get("quiz_id"))

        if not context.get("is_valid_for_mastery"):
            skipped_assessments.append(
                {
                    "source_type": "quiz_grade",
                    "quiz_moodle_id": quiz_id,
                    "name": context.get("quiz_name"),
                    "status": "skipped",
                    "reasons": context.get("skip_reasons", []),
                }
            )
            continue

        included.append(
            {
                "source_type": "quiz_grade",
                "quiz_moodle_id": quiz_id,
                "course_module_id": context.get("course_module_id"),
                "name": context.get("quiz_name"),
                "weight_percent": quiz_weights.get(quiz_id),
                "evidence_count": len(context.get("competency_mappings", [])),
                "status": "included",
            }
        )

    return included


def _build_ai_learning_profile_input(
    student: dict,
    course: dict,
    mastery_report: dict,
    calculated_weak_areas: list[dict],
    assignment_evidence: list[dict],
    quiz_evidence: list[dict],
    included_assessments: list[dict],
) -> dict:
    """
    Builds the course-level payload sent to the LLM.
    """

    return {
        "request_type": "generate_course_learning_profile",
        "student": student,
        "course": course,
        "included_assessments": included_assessments,
        "calculated_mastery_result": mastery_report,
        "calculated_weak_areas": calculated_weak_areas,
        "assignment_evidence": assignment_evidence,
        "quiz_evidence": quiz_evidence,
        "ai_rules": [
            "Do not invent or modify mastery scores.",
            "Do not infer missing assignment or quiz competency mappings.",
            "Only explain weak areas supported by calculated_weak_areas or evidence.",
            "Do not treat AI-generated quiz questions as Moodle quiz results.",
        ],
    }


def generate_learning_report_for_assignment(
    student_user_id: int,
    course_id: int,
    assignment_id: int,
    student_name: str | None = None,
    course_name: str | None = None,
    assignment_weight_percent: float = 100.0,
    explicit_mappings: dict | list | None = None,
) -> dict:
    """
    Runs the complete SkillSync AI component for one Moodle assignment.

    Flow:
    1. Fetch live Moodle assignment/submission/rubric data.
    2. Resolve rubric criterion -> competency mappings.
    3. Calculate mastery scores with normal Python logic.
    4. Send calculated evidence to the selected AI provider.
    5. Return one final learning report object ready for Supabase/backend use.
    """

    settings = get_settings()

    client = MoodleClient(
        base_url=settings.moodle_base_url,
        token=settings.moodle_token,
        rest_format=settings.moodle_rest_format,
    )

    assignment_context = build_student_assignment_context(
        client=client,
        student_user_id=student_user_id,
        course_id=course_id,
        assignment_id=assignment_id,
    )

    criterion_mapping = build_ai_criterion_mapping_from_moodle(
        client=client,
        course_module_id=assignment_context["course_module_id"],
        assignment_id=assignment_id,
        explicit_mappings=explicit_mappings,
    )

    student_competency_evidence = build_student_rubric_evidence(
        student_id=student_user_id,
        assignment_id=assignment_id,
        rubric_fillings=assignment_context.get("rubric", {}).get("rubric_fillings", []),
        criterion_mapping=criterion_mapping,
    )

    assignment_ai_input = build_assignment_ai_input(
        assignment_context=assignment_context,
        student_name=student_name,
        course_name=course_name,
        criterion_mapping=criterion_mapping,
    )

    mastery_inputs = build_mastery_inputs_from_assignment_ai_input(
        ai_input=assignment_ai_input,
        assignment_weight_percent=assignment_weight_percent,
    )

    mastery_report = calculate_mastery_report(
        student_id=mastery_inputs.student_id,
        course_id=mastery_inputs.course_id,
        silos=mastery_inputs.silos,
        assessments=mastery_inputs.assessments,
        mappings=mastery_inputs.mappings,
        results=mastery_inputs.student_results,
    )

    mastery_report_dict = mastery_report_to_dict(mastery_report)
    calculated_weak_areas = _build_calculated_weak_areas(mastery_report_dict)

    ai_learning_support_input = _build_ai_learning_support_input(
        assignment_ai_input=assignment_ai_input,
        mastery_report=mastery_report_dict,
        calculated_weak_areas=calculated_weak_areas,
    )

    ai_provider = get_ai_provider()
    ai_feedback = ai_provider.generate_feedback(ai_learning_support_input)

    generated_at = _now_iso()
    report_key = build_report_key(
        student_user_id=student_user_id,
        course_id=course_id,
        assignment_id=assignment_id,
    )

    return {
        "schema_version": "1.0",
        "report_key": report_key,
        "generated_at": generated_at,
        "source": {
            "system": "moodle",
            "data_type": "assignment_learning_report",
        },
        "student": assignment_ai_input["student"],
        "course": assignment_ai_input["course"],
        "assessment": assignment_ai_input["assessment"],
        "performance": assignment_ai_input["performance"],
        "teacher_feedback": assignment_ai_input["teacher_feedback"],
        "criterion_mapping": criterion_mapping,
        "student_competency_evidence": student_rubric_evidence_to_dicts(
            student_competency_evidence
        ),
        "mastery_report": mastery_report_dict,
        "calculated_weak_areas": calculated_weak_areas,
        "ai_learning_support_input": ai_learning_support_input,
        "ai_feedback": ai_feedback.model_dump(),
        "metadata": {
            "ai_provider": settings.ai_provider,
            "ai_model": _get_ai_model_name(),
            "assignment_weight_percent": assignment_weight_percent,
            "mastery_calculated_outside_llm": True,
        },
    }


def generate_student_learning_profile(
    student_user_id: int,
    course_id: int,
    student_name: str | None = None,
    course_name: str | None = None,
    assignment_ids: list[int] | None = None,
    quiz_ids: list[int] | None = None,
    assessment_weights: dict | None = None,
    explicit_assignment_mappings: dict | list | None = None,
    explicit_quiz_mappings: dict | list | None = None,
) -> dict:
    """
    Generates one course-level mastery profile from assignment and quiz evidence.

    Assignment evidence continues to use rubric criterion scores. Quiz evidence
    uses Moodle's best/final quiz grade as one evidence item per completed quiz.
    """

    settings = get_settings()

    client = MoodleClient(
        base_url=settings.moodle_base_url,
        token=settings.moodle_token,
        rest_format=settings.moodle_rest_format,
    )

    resolved_assignment_ids = _resolve_assignment_ids(
        client=client,
        course_id=course_id,
        assignment_ids=assignment_ids,
    )
    resolved_quiz_ids = _resolve_quiz_ids(
        client=client,
        course_id=course_id,
        quiz_ids=quiz_ids,
    )

    assignment_items = []
    skipped_assessments = []

    for assignment_id in resolved_assignment_ids:
        try:
            assignment_item = _build_assignment_profile_item(
                client=client,
                student_user_id=student_user_id,
                course_id=course_id,
                assignment_id=assignment_id,
                student_name=student_name,
                course_name=course_name,
                explicit_mappings=explicit_assignment_mappings,
            )
        except Exception as error:
            skipped_assessments.append(
                {
                    "source_type": "assignment_rubric",
                    "assignment_moodle_id": str(assignment_id),
                    "status": "skipped",
                    "reasons": [str(error)],
                }
            )
            continue

        if _assignment_item_has_mastery_evidence(assignment_item):
            assignment_items.append(assignment_item)
        else:
            skipped_assessments.append(
                {
                    "source_type": "assignment_rubric",
                    "assignment_moodle_id": str(assignment_id),
                    "name": (
                        assignment_item
                        .get("assignment_ai_input", {})
                        .get("assessment", {})
                        .get("name")
                    ),
                    "status": "skipped",
                    "reasons": ["missing_rubric_competency_evidence"],
                }
            )

    quiz_contexts = build_student_course_quiz_contexts(
        client=client,
        student_user_id=student_user_id,
        course_id=course_id,
        quiz_ids=resolved_quiz_ids,
        explicit_mappings=explicit_quiz_mappings,
    )

    valid_quiz_contexts = [
        context for context in quiz_contexts
        if context.get("is_valid_for_mastery")
    ]

    included_activity_count = len(assignment_items) + len(valid_quiz_contexts)
    fallback_weight = (
        round(100.0 / included_activity_count, 2)
        if included_activity_count
        else 0.0
    )

    assignment_weights = {}
    quiz_weights = {}
    weight_sources = {}

    for item in assignment_items:
        assignment_id = _normalise_id(item.get("assignment_id"))
        configured_weight = _lookup_assessment_weight(
            assessment_weights=assessment_weights,
            source_type="assignment",
            assessment_id=assignment_id,
        )
        assignment_weights[assignment_id] = configured_weight or fallback_weight
        weight_sources[f"assignment:{assignment_id}"] = (
            "configured" if configured_weight is not None else "equal_fallback"
        )

    for context in valid_quiz_contexts:
        quiz_id = _normalise_id(context.get("quiz_id"))
        configured_weight = _lookup_assessment_weight(
            assessment_weights=assessment_weights,
            source_type="quiz",
            assessment_id=quiz_id,
        )
        quiz_weights[quiz_id] = configured_weight or fallback_weight
        weight_sources[f"quiz:{quiz_id}"] = (
            "configured" if configured_weight is not None else "equal_fallback"
        )

    assignment_mastery_bundles = []

    for item in assignment_items:
        assignment_id = _normalise_id(item.get("assignment_id"))
        assignment_mastery_bundles.append(
            build_mastery_inputs_from_assignment_ai_input(
                ai_input=item["assignment_ai_input"],
                assignment_weight_percent=assignment_weights[assignment_id],
            )
        )

    quiz_mastery_bundle = build_mastery_inputs_from_quiz_contexts(
        quiz_contexts=quiz_contexts,
        quiz_weight_percent_by_id=quiz_weights,
    )

    mastery_inputs = merge_mastery_input_bundles(
        student_id=str(student_user_id),
        course_id=str(course_id),
        bundles=[
            *assignment_mastery_bundles,
            quiz_mastery_bundle,
        ],
    )

    mastery_report = calculate_mastery_report(
        student_id=mastery_inputs.student_id,
        course_id=mastery_inputs.course_id,
        silos=mastery_inputs.silos,
        assessments=mastery_inputs.assessments,
        mappings=mastery_inputs.mappings,
        results=mastery_inputs.student_results,
    )

    mastery_report_dict = mastery_report_to_dict(mastery_report)
    calculated_weak_areas = _build_calculated_weak_areas(mastery_report_dict)

    assignment_evidence = []

    for item in assignment_items:
        assignment_evidence.extend(
            student_rubric_evidence_to_dicts(
                item.get("student_competency_evidence", [])
            )
        )

    quiz_evidence = [
        context for context in quiz_contexts
        if context.get("is_valid_for_mastery")
    ]

    student_evidence = []

    for item in assignment_items:
        student_evidence.extend(_build_assignment_student_evidence_rows(item))

    student_evidence.extend(_build_quiz_student_evidence_rows(quiz_contexts))

    included_assessments = _build_included_assessments(
        assignment_items=assignment_items,
        quiz_contexts=quiz_contexts,
        assignment_weights=assignment_weights,
        quiz_weights=quiz_weights,
        skipped_assessments=skipped_assessments,
    )

    student = {
        "moodle_user_id": student_user_id,
        "name": student_name,
    }
    course = {
        "course_id": course_id,
        "course_name": course_name,
    }

    ai_learning_profile_input = _build_ai_learning_profile_input(
        student=student,
        course=course,
        mastery_report=mastery_report_dict,
        calculated_weak_areas=calculated_weak_areas,
        assignment_evidence=assignment_evidence,
        quiz_evidence=quiz_evidence,
        included_assessments=included_assessments,
    )

    ai_provider = get_ai_provider()
    ai_feedback = ai_provider.generate_feedback(ai_learning_profile_input)

    generated_at = _now_iso()
    report_key = build_course_profile_key(
        student_user_id=student_user_id,
        course_id=course_id,
    )

    return {
        "schema_version": "1.1",
        "report_type": "course_learning_profile",
        "report_key": report_key,
        "generated_at": generated_at,
        "source": {
            "system": "moodle",
            "data_type": "course_learning_profile",
        },
        "student": student,
        "course": course,
        "included_assessments": included_assessments,
        "skipped_assessments": skipped_assessments,
        "assignment_evidence": assignment_evidence,
        "quiz_evidence": quiz_evidence,
        "student_evidence": student_evidence,
        "mastery_report": mastery_report_dict,
        "calculated_weak_areas": calculated_weak_areas,
        "ai_learning_support_input": ai_learning_profile_input,
        "ai_feedback": ai_feedback.model_dump(),
        "metadata": {
            "ai_provider": settings.ai_provider,
            "ai_model": _get_ai_model_name(),
            "assessment_weighting": {
                "weights": {
                    "assignments": assignment_weights,
                    "quizzes": quiz_weights,
                },
                "sources": weight_sources,
                "default_strategy": "equal_weight_across_included_activities",
            },
            "quiz_attempt_function": "mod_quiz_get_user_quiz_attempts",
            "mastery_calculated_outside_llm": True,
        },
    }
