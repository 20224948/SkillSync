from dataclasses import dataclass

from mastery.mastery_model import (
    SILO,
    Assessment,
    AssessmentSiloMapping,
    StudentResult,
)


@dataclass
class MasteryInputBundle:
    """
    Groups the converted Mastery Model input objects together.

    This makes it easier to pass Moodle-derived data into the existing
    calculate_mastery_report() function.
    """

    student_id: str
    course_id: str
    silos: list[SILO]
    assessments: list[Assessment]
    mappings: list[AssessmentSiloMapping]
    student_results: list[StudentResult]


def _normalise_id(value: object) -> str:
    """
    Converts Moodle IDs into strings for consistent Mastery Model IDs.
    """

    return str(value).strip()


def _safe_float(value: object) -> float | None:
    """
    Safely converts a value into a float.

    Returns None if the value cannot be converted.
    """

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_score(score: float) -> float:
    """
    Keeps a score between 0 and 100.
    """

    return max(0, min(100, score))


def _get_valid_rubric_evidence(ai_input: dict) -> list[dict]:
    """
    Returns rubric evidence entries that contain enough data for mastery scoring.

    Required fields:
    - silo_id
    - score_percent
    """

    valid_items = []

    for item in ai_input.get("rubric_evidence", []):
        silo_id = item.get("silo_id")
        score_percent = _safe_float(item.get("score_percent"))

        if not silo_id:
            continue

        if score_percent is None:
            continue

        valid_items.append(item)

    return valid_items


def _calculate_rubric_criterion_weights(
    rubric_evidence: list[dict],
    assignment_weight_percent: float,
) -> dict[str, float]:
    """
    Calculates how much each rubric criterion should contribute to mastery.

    If max_score values are available, each criterion is weighted based on its
    share of the rubric's total points.

    Example:
    - Assignment weight = 40%
    - Four rubric criteria, each worth 25 points
    - Each criterion contributes 10% evidence weight

    If max_score values are missing, the assignment weight is split evenly.
    """

    weights: dict[str, float] = {}

    total_max_score = sum(
        _safe_float(item.get("max_score")) or 0
        for item in rubric_evidence
    )

    if total_max_score > 0:
        for item in rubric_evidence:
            criterion_id = item.get("criterion_id")
            max_score = _safe_float(item.get("max_score")) or 0

            if criterion_id is None:
                continue

            weights[_normalise_id(criterion_id)] = round(
                assignment_weight_percent * (max_score / total_max_score),
                2,
            )

        return weights

    # Fallback: split the assignment weight evenly across all valid rubric criteria.
    if not rubric_evidence:
        return weights

    equal_weight = round(assignment_weight_percent / len(rubric_evidence), 2)

    for item in rubric_evidence:
        criterion_id = item.get("criterion_id")

        if criterion_id is not None:
            weights[_normalise_id(criterion_id)] = equal_weight

    return weights


def build_mastery_inputs_from_assignment_ai_input(
    ai_input: dict,
    assignment_weight_percent: float = 100.0,
) -> MasteryInputBundle:
    """
    Converts Moodle assignment AI input into Mastery Model input objects.

    This function uses rubric evidence as the main source of SILO mastery data.

    It creates:
    - one SILO per unique rubric SILO
    - one assessment evidence item per rubric criterion
    - one mapping from each rubric criterion assessment to its related SILO
    - one student result per rubric criterion score

    This is more accurate than applying the overall assignment grade to every
    SILO, because each rubric criterion can produce its own SILO-level score.
    """

    student = ai_input.get("student", {})
    course = ai_input.get("course", {})
    assessment = ai_input.get("assessment", {})

    student_id = _normalise_id(student.get("moodle_user_id"))
    course_id = _normalise_id(course.get("course_id"))
    assignment_id = _normalise_id(assessment.get("assignment_id"))
    assignment_name = assessment.get("name") or f"Assignment {assignment_id}"

    rubric_evidence = _get_valid_rubric_evidence(ai_input)

    criterion_weights = _calculate_rubric_criterion_weights(
        rubric_evidence=rubric_evidence,
        assignment_weight_percent=assignment_weight_percent,
    )

    silos_by_id: dict[str, SILO] = {}
    assessments: list[Assessment] = []
    mappings: list[AssessmentSiloMapping] = []
    student_results: list[StudentResult] = []

    for item in rubric_evidence:
        silo_id = _normalise_id(item.get("silo_id"))
        criterion_id = item.get("criterion_id")

        if criterion_id is None:
            continue

        criterion_id = _normalise_id(criterion_id)
        criterion_title = item.get("criterion_title") or f"Rubric criterion {criterion_id}"
        silo_description = item.get("silo_description") or criterion_title
        score_percent = _safe_float(item.get("score_percent"))

        if score_percent is None:
            continue

        # Create the SILO once.
        if silo_id not in silos_by_id:
            silos_by_id[silo_id] = SILO(
                silo_id=silo_id,
                course_id=course_id,
                title=criterion_title,
                description=silo_description,
            )

        # Create a pseudo-assessment for this rubric criterion.
        # This lets the existing Mastery Model calculate per-SILO mastery
        # without needing to rewrite the mastery formula.
        assessment_id = f"{assignment_id}-criterion-{criterion_id}"

        evidence_weight = criterion_weights.get(
            criterion_id,
            round(assignment_weight_percent / max(len(rubric_evidence), 1), 2),
        )

        assessments.append(
            Assessment(
                assessment_id=assessment_id,
                course_id=course_id,
                name=f"{assignment_name} - {criterion_title}",
                weight_percent=evidence_weight,
            )
        )

        # This rubric criterion maps directly to one SILO.
        mappings.append(
            AssessmentSiloMapping(
                assessment_id=assessment_id,
                silo_id=silo_id,
                coverage_weight=1.0,
            )
        )

        # The student's result for this pseudo-assessment is the rubric score.
        student_results.append(
            StudentResult(
                student_id=student_id,
                assessment_id=assessment_id,
                score_percent=score_percent,
            )
        )

    return MasteryInputBundle(
        student_id=student_id,
        course_id=course_id,
        silos=list(silos_by_id.values()),
        assessments=assessments,
        mappings=mappings,
        student_results=student_results,
    )


def build_mastery_inputs_from_quiz_contexts(
    quiz_contexts: list[dict],
    quiz_weight_percent_by_id: dict[str, float] | None = None,
) -> MasteryInputBundle:
    """
    Converts normalised Moodle quiz evidence into Mastery Model input objects.

    Each quiz becomes one assessment evidence item. If a quiz maps to multiple
    competencies/SILOs, coverage_weight controls how much of the quiz supports
    each SILO.
    """

    quiz_weight_percent_by_id = quiz_weight_percent_by_id or {}

    valid_contexts = [
        context for context in quiz_contexts
        if context.get("is_valid_for_mastery")
    ]

    if not valid_contexts:
        return MasteryInputBundle(
            student_id="",
            course_id="",
            silos=[],
            assessments=[],
            mappings=[],
            student_results=[],
        )

    first_context = valid_contexts[0]
    student_id = _normalise_id(first_context.get("student_user_id"))
    course_id = _normalise_id(first_context.get("course_id"))

    silos_by_id: dict[str, SILO] = {}
    assessments: list[Assessment] = []
    mappings: list[AssessmentSiloMapping] = []
    student_results: list[StudentResult] = []

    fallback_weight = round(100.0 / len(valid_contexts), 2)

    for context in valid_contexts:
        quiz_id = _normalise_id(context.get("quiz_id"))
        quiz_name = context.get("quiz_name") or f"Quiz {quiz_id}"
        assessment_id = f"quiz-{quiz_id}"
        grade_percent = _safe_float(
            context.get("best_grade", {}).get("grade_percent")
        )

        if grade_percent is None:
            continue

        quiz_weight_percent = _safe_float(
            quiz_weight_percent_by_id.get(quiz_id)
        )

        if quiz_weight_percent is None:
            quiz_weight_percent = fallback_weight

        assessments.append(
            Assessment(
                assessment_id=assessment_id,
                course_id=course_id,
                name=quiz_name,
                weight_percent=quiz_weight_percent,
            )
        )

        student_results.append(
            StudentResult(
                student_id=student_id,
                assessment_id=assessment_id,
                score_percent=_clamp_score(grade_percent),
            )
        )

        for competency_mapping in context.get("competency_mappings", []):
            silo_id = _normalise_id(
                competency_mapping.get("silo_id")
                or competency_mapping.get("competency_code")
                or competency_mapping.get("competency_id")
            )

            if not silo_id:
                continue

            coverage_weight = _safe_float(
                competency_mapping.get("coverage_weight")
            )

            if coverage_weight is None or coverage_weight <= 0:
                continue

            silo_title = (
                competency_mapping.get("competency_code")
                or competency_mapping.get("competency_name")
                or silo_id
            )
            silo_description = (
                competency_mapping.get("silo_description")
                or competency_mapping.get("competency_name")
                or silo_title
            )

            if silo_id not in silos_by_id:
                silos_by_id[silo_id] = SILO(
                    silo_id=silo_id,
                    course_id=course_id,
                    title=silo_title,
                    description=silo_description,
                )

            mappings.append(
                AssessmentSiloMapping(
                    assessment_id=assessment_id,
                    silo_id=silo_id,
                    coverage_weight=coverage_weight,
                )
            )

    return MasteryInputBundle(
        student_id=student_id,
        course_id=course_id,
        silos=list(silos_by_id.values()),
        assessments=assessments,
        mappings=mappings,
        student_results=student_results,
    )


def merge_mastery_input_bundles(
    student_id: str,
    course_id: str,
    bundles: list[MasteryInputBundle],
) -> MasteryInputBundle:
    """
    Combines multiple evidence-source bundles into one mastery input bundle.
    """

    normalised_student_id = _normalise_id(student_id)
    normalised_course_id = _normalise_id(course_id)

    silos_by_id: dict[str, SILO] = {}
    assessments_by_id: dict[str, Assessment] = {}
    mappings: list[AssessmentSiloMapping] = []
    student_results: list[StudentResult] = []

    for bundle in bundles:
        for silo in bundle.silos:
            if silo.silo_id not in silos_by_id:
                silos_by_id[silo.silo_id] = silo

        for assessment in bundle.assessments:
            if assessment.assessment_id not in assessments_by_id:
                assessments_by_id[assessment.assessment_id] = assessment

        mappings.extend(bundle.mappings)
        student_results.extend(bundle.student_results)

    return MasteryInputBundle(
        student_id=normalised_student_id,
        course_id=normalised_course_id,
        silos=list(silos_by_id.values()),
        assessments=list(assessments_by_id.values()),
        mappings=mappings,
        student_results=student_results,
    )
