from __future__ import annotations

import html
import re
from typing import Any

from moodle.client import MoodleClient
from moodle.evidence_mapper import normalise_competencies_from_moodle_response
from moodle.services.competencies import get_course_module_competencies
from moodle.services.quizzes import (
    find_quiz_by_id,
    get_quizzes_by_course,
    get_user_best_grade,
    get_user_quiz_attempts,
)


COMPLETED_ATTEMPT_STATES = {"finished", "submitted"}


def clean_html_text(value: object) -> str:
    """
    Converts Moodle HTML-ish fields into plain text.
    """

    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def _normalise_id(value: object) -> str:
    """
    Converts Moodle IDs into strings for stable internal matching.
    """

    return str(value).strip()


def _safe_float(value: object) -> float | None:
    """
    Safely converts Moodle numeric values into floats.
    """

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_percent(value: float) -> float:
    """
    Keeps percentage scores within the mastery model's expected range.
    """

    return max(0.0, min(100.0, value))


def _extract_attempts(attempts_response: dict | list | None) -> list[dict]:
    """
    Extracts attempt dictionaries from Moodle's attempts response.
    """

    if isinstance(attempts_response, dict):
        attempts = attempts_response.get("attempts", [])
        return attempts if isinstance(attempts, list) else []

    if isinstance(attempts_response, list):
        return attempts_response

    return []


def _is_completed_attempt(attempt: dict) -> bool:
    """
    Returns True when an attempt can be considered completed evidence.
    """

    state = str(attempt.get("state") or "").strip().lower()

    return state in COMPLETED_ATTEMPT_STATES


def _select_completed_attempt(attempts: list[dict]) -> dict | None:
    """
    Chooses the best available completed attempt for audit metadata.

    The mastery score itself uses mod_quiz_get_user_best_grade. This selected
    attempt is stored so the report can show which completed attempt supported
    the evidence.
    """

    completed_attempts = [
        attempt for attempt in attempts
        if _is_completed_attempt(attempt)
    ]

    if not completed_attempts:
        return None

    def sort_key(attempt: dict) -> tuple[float, int, int, int]:
        sumgrades = _safe_float(attempt.get("sumgrades"))

        return (
            sumgrades if sumgrades is not None else -1.0,
            int(attempt.get("timefinish") or 0),
            int(attempt.get("timemodified") or 0),
            int(attempt.get("attempt") or 0),
        )

    return sorted(completed_attempts, key=sort_key, reverse=True)[0]


def _normalise_attempt(attempt: dict | None) -> dict | None:
    """
    Keeps the useful attempt metadata only.
    """

    if not attempt:
        return None

    return {
        "attempt_id": attempt.get("id"),
        "attempt_number": attempt.get("attempt"),
        "unique_id": attempt.get("uniqueid"),
        "state": attempt.get("state"),
        "sumgrades": _safe_float(attempt.get("sumgrades")),
        "time_started": attempt.get("timestart"),
        "time_finished": attempt.get("timefinish"),
        "time_modified": attempt.get("timemodified"),
    }


def _normalise_best_grade(
    best_grade_response: dict | list | None,
    quiz_max_grade: float | None,
) -> dict:
    """
    Extracts and normalises a student's best quiz grade.
    """

    response = best_grade_response if isinstance(best_grade_response, dict) else {}
    has_grade = bool(response.get("hasgrade"))
    raw_grade = _safe_float(response.get("grade"))
    grade_percent = None

    if has_grade and raw_grade is not None and quiz_max_grade and quiz_max_grade > 0:
        grade_percent = round(_clamp_percent((raw_grade / quiz_max_grade) * 100), 2)

    return {
        "has_grade": has_grade,
        "grade": raw_grade,
        "grade_percent": grade_percent,
        "max_grade": quiz_max_grade,
    }


def _iter_explicit_mapping_items(
    explicit_mappings: dict | list | None,
    quiz_id: str,
) -> list[dict]:
    """
    Accepts flexible explicit quiz mapping formats.

    Supported examples:
    {"12": "IT101-SILO1"}
    {"12": {"competency_id": "123", "coverage_weight": 1.0}}
    {"12": [{"competency_id": "123"}, {"competency_id": "124"}]}
    [{"quiz_id": "12", "competency_id": "123", "coverage_weight": 0.5}]
    {"mappings": [{"quiz_id": "12", "competency_id": "123"}]}
    """

    if explicit_mappings is None:
        return []

    if isinstance(explicit_mappings, dict) and isinstance(explicit_mappings.get("mappings"), list):
        explicit_mappings = explicit_mappings["mappings"]

    items: list[dict] = []

    if isinstance(explicit_mappings, dict):
        value = explicit_mappings.get(quiz_id)

        if value is None:
            return []

        if isinstance(value, list):
            raw_items = value
        else:
            raw_items = [value]

        for raw_item in raw_items:
            if isinstance(raw_item, dict):
                item = dict(raw_item)
            else:
                item = {"competency_id": raw_item}

            item["quiz_id"] = quiz_id
            items.append(item)

        return items

    if isinstance(explicit_mappings, list):
        for raw_item in explicit_mappings:
            if not isinstance(raw_item, dict):
                continue

            item_quiz_id = raw_item.get("quiz_id")

            if item_quiz_id is not None and _normalise_id(item_quiz_id) != quiz_id:
                continue

            if raw_item.get("competency_id") is None and raw_item.get("silo_id") is None:
                continue

            items.append(dict(raw_item))

    return items


def _apply_coverage_weights(mappings: list[dict]) -> list[dict]:
    """
    Adds coverage weights when they are not supplied explicitly.
    """

    if not mappings:
        return []

    provided_weights = [
        _safe_float(mapping.get("coverage_weight"))
        for mapping in mappings
    ]

    if all(weight is not None and weight > 0 for weight in provided_weights):
        return [
            {
                **mapping,
                "coverage_weight": float(provided_weights[index]),
            }
            for index, mapping in enumerate(mappings)
        ]

    equal_weight = round(1.0 / len(mappings), 4)

    return [
        {
            **mapping,
            "coverage_weight": equal_weight,
        }
        for mapping in mappings
    ]


def _build_explicit_competency_mappings(
    quiz_id: str,
    explicit_mappings: dict | list | None,
    competencies_by_id: dict[str, object],
) -> list[dict]:
    """
    Converts explicit backend/config mappings into quiz competency mappings.
    """

    mappings = []

    for item in _iter_explicit_mapping_items(
        explicit_mappings=explicit_mappings,
        quiz_id=quiz_id,
    ):
        competency_id = item.get("competency_id") or item.get("silo_id")

        if competency_id is None:
            continue

        competency_id = _normalise_id(competency_id)
        linked_competency = competencies_by_id.get(competency_id)

        competency_code = (
            item.get("competency_code")
            or item.get("silo_id")
            or getattr(linked_competency, "code", None)
            or competency_id
        )
        competency_name = (
            item.get("competency_name")
            or item.get("title")
            or getattr(linked_competency, "name", None)
            or competency_code
        )
        description = (
            item.get("silo_description")
            or item.get("description")
            or getattr(linked_competency, "description", None)
            or competency_name
        )

        mappings.append(
            {
                "quiz_id": quiz_id,
                "competency_id": competency_id,
                "competency_code": clean_html_text(competency_code),
                "competency_name": clean_html_text(competency_name),
                "silo_id": clean_html_text(item.get("silo_id") or competency_code),
                "silo_description": clean_html_text(description),
                "coverage_weight": _safe_float(item.get("coverage_weight")),
                "mapping_source": "explicit",
            }
        )

    return _apply_coverage_weights(mappings)


def _build_moodle_competency_mappings(
    quiz_id: str,
    competencies: list[object],
) -> list[dict]:
    """
    Converts Moodle activity-level competencies into quiz mastery mappings.
    """

    mappings = []

    for competency in competencies:
        competency_code = getattr(competency, "code", "") or getattr(competency, "id", "")
        competency_name = getattr(competency, "name", "") or competency_code
        description = getattr(competency, "description", "") or competency_name

        mappings.append(
            {
                "quiz_id": quiz_id,
                "competency_id": getattr(competency, "id", competency_code),
                "competency_code": competency_code,
                "competency_name": competency_name,
                "silo_id": competency_code or getattr(competency, "id", ""),
                "silo_description": description,
                "coverage_weight": None,
                "mapping_source": "moodle_activity_competency",
            }
        )

    return _apply_coverage_weights(mappings)


def build_quiz_competency_mappings(
    quiz_id: int | str,
    competencies_response: dict | list,
    explicit_mappings: dict | list | None = None,
) -> list[dict]:
    """
    Resolves quiz -> competency mappings.

    Explicit mappings win. If none are supplied for this quiz, the normaliser
    uses competencies linked directly to the Moodle quiz activity.
    """

    quiz_id_text = _normalise_id(quiz_id)
    competencies = normalise_competencies_from_moodle_response(competencies_response)
    competencies_by_id = {
        _normalise_id(getattr(competency, "id", "")): competency
        for competency in competencies
    }

    explicit = _build_explicit_competency_mappings(
        quiz_id=quiz_id_text,
        explicit_mappings=explicit_mappings,
        competencies_by_id=competencies_by_id,
    )

    if explicit:
        return explicit

    return _build_moodle_competency_mappings(
        quiz_id=quiz_id_text,
        competencies=competencies,
    )


def normalise_student_quiz_context(
    quiz: dict,
    attempts_response: dict | list | None,
    best_grade_response: dict | list | None,
    competencies_response: dict | list,
    student_user_id: int,
    course_id: int,
    explicit_mappings: dict | list | None = None,
) -> dict:
    """
    Converts Moodle quiz responses into clean mastery-ready quiz evidence.
    """

    quiz_id = quiz.get("id")
    course_module_id = quiz.get("coursemodule")
    quiz_max_grade = _safe_float(quiz.get("grade"))
    attempts = _extract_attempts(attempts_response)
    selected_attempt = _select_completed_attempt(attempts)
    best_grade = _normalise_best_grade(
        best_grade_response=best_grade_response,
        quiz_max_grade=quiz_max_grade,
    )

    competency_mappings = build_quiz_competency_mappings(
        quiz_id=quiz_id,
        competencies_response=competencies_response,
        explicit_mappings=explicit_mappings,
    )

    skip_reasons = []

    if selected_attempt is None:
        skip_reasons.append("no_completed_attempt")

    if not best_grade["has_grade"] or best_grade["grade_percent"] is None:
        skip_reasons.append("missing_best_grade")

    if not competency_mappings:
        skip_reasons.append("missing_competency_mapping")

    return {
        "source": "moodle",
        "data_type": "quiz_learning_evidence",
        "student_user_id": student_user_id,
        "course_id": course_id,
        "quiz_id": quiz_id,
        "course_module_id": course_module_id,
        "quiz_name": quiz.get("name"),
        "quiz_intro": clean_html_text(quiz.get("intro")),
        "quiz_max_grade": quiz_max_grade,
        "best_grade": best_grade,
        "selected_attempt": _normalise_attempt(selected_attempt),
        "attempt_count": len(attempts),
        "completed_attempt_count": len([
            attempt for attempt in attempts
            if _is_completed_attempt(attempt)
        ]),
        "competency_mappings": competency_mappings,
        "is_valid_for_mastery": not skip_reasons,
        "skip_reasons": skip_reasons,
    }


def build_student_quiz_context(
    client: MoodleClient,
    student_user_id: int,
    course_id: int,
    quiz_id: int,
    explicit_mappings: dict | list | None = None,
) -> dict:
    """
    Builds clean quiz evidence for one student and one Moodle quiz.
    """

    quizzes_response = get_quizzes_by_course(
        client=client,
        course_id=course_id,
    )

    quiz = find_quiz_by_id(
        quizzes_response=quizzes_response,
        quiz_id=quiz_id,
    )

    if quiz is None:
        raise ValueError(
            f"Could not find quiz_id={quiz_id} in course_id={course_id}."
        )

    attempts_response = get_user_quiz_attempts(
        client=client,
        quiz_id=quiz_id,
        user_id=student_user_id,
        status="all",
    )

    best_grade_response = get_user_best_grade(
        client=client,
        quiz_id=quiz_id,
        user_id=student_user_id,
    )

    course_module_id = quiz.get("coursemodule")

    if course_module_id is None:
        raise ValueError(
            f"Quiz {quiz_id} was found, but no course module ID was returned."
        )

    competencies_response = get_course_module_competencies(
        client=client,
        course_module_id=int(course_module_id),
    )

    return normalise_student_quiz_context(
        quiz=quiz,
        attempts_response=attempts_response,
        best_grade_response=best_grade_response,
        competencies_response=competencies_response,
        student_user_id=student_user_id,
        course_id=course_id,
        explicit_mappings=explicit_mappings,
    )


def build_student_course_quiz_contexts(
    client: MoodleClient,
    student_user_id: int,
    course_id: int,
    quiz_ids: list[int] | None = None,
    explicit_mappings: dict | list | None = None,
) -> list[dict]:
    """
    Builds clean quiz evidence for selected quizzes, or all quizzes in a course.
    """

    quizzes_response = get_quizzes_by_course(
        client=client,
        course_id=course_id,
    )

    quizzes = quizzes_response.get("quizzes", [])
    selected_quiz_ids = (
        None
        if quiz_ids is None
        else set(quiz_ids)
    )

    contexts = []

    for quiz in quizzes:
        quiz_id = quiz.get("id")

        if quiz_id is None:
            continue

        if selected_quiz_ids is not None and quiz_id not in selected_quiz_ids:
            continue

        attempts_response = get_user_quiz_attempts(
            client=client,
            quiz_id=int(quiz_id),
            user_id=student_user_id,
            status="all",
        )

        best_grade_response = get_user_best_grade(
            client=client,
            quiz_id=int(quiz_id),
            user_id=student_user_id,
        )

        course_module_id = quiz.get("coursemodule")

        if course_module_id is None:
            competencies_response = []
        else:
            competencies_response = get_course_module_competencies(
                client=client,
                course_module_id=int(course_module_id),
            )

        contexts.append(
            normalise_student_quiz_context(
                quiz=quiz,
                attempts_response=attempts_response,
                best_grade_response=best_grade_response,
                competencies_response=competencies_response,
                student_user_id=student_user_id,
                course_id=course_id,
                explicit_mappings=explicit_mappings,
            )
        )

    return contexts
