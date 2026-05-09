from typing import Any


NEGATIVE_INDICATORS = [
    "limited",
    "unclear",
    "basic",
    "poor",
    "vague",
    "generic",
    "not well",
    "needs",
    "missing",
    "does not",
    "less",
    "not enough",
]


def _contains_improvement_signal(text: str | None) -> bool:
    """
    Checks whether a feedback/rubric remark appears to indicate a weak area.

    This is a lightweight fallback. If a rubric criterion mapping with scores
    is provided, score-based weak area detection is preferred.
    """

    if not text:
        return False

    text_lower = text.lower()

    return any(indicator in text_lower for indicator in NEGATIVE_INDICATORS)


def _summarise_submitted_files(assignment_context: dict) -> list[dict]:
    """
    Keeps only useful submitted file metadata for the AI.

    The AI does not need every Moodle file field, only enough context to know
    what was submitted.
    """

    submitted_files = (
        assignment_context
        .get("submission", {})
        .get("submitted_files", [])
    )

    return [
        {
            "filename": file.get("filename"),
            "mimetype": file.get("mimetype"),
            "filesize": file.get("filesize"),
            "fileurl": file.get("fileurl"),
        }
        for file in submitted_files
    ]


def _summarise_feedback_files(assignment_context: dict) -> list[dict]:
    """
    Keeps useful teacher feedback files only.

    Moodle may return many editpdf files such as stamps and page images.
    For AI input, we usually only care about actual PDF feedback files.
    """

    feedback_files = (
        assignment_context
        .get("feedback", {})
        .get("feedback_files", [])
    )

    useful_files = []

    for file in feedback_files:
        is_pdf = file.get("mimetype") == "application/pdf"
        is_useful_area = file.get("area") in ["combined", "download", "feedback"]

        if is_pdf and is_useful_area:
            useful_files.append(
                {
                    "filename": file.get("filename"),
                    "area": file.get("area"),
                    "mimetype": file.get("mimetype"),
                    "fileurl": file.get("fileurl"),
                }
            )

    return useful_files


def _lookup_level_score(levels: dict, level_id: object) -> object:
    """
    Finds a Moodle rubric level score without losing valid zero scores.
    """

    if level_id in levels:
        return levels[level_id]

    level_id_text = str(level_id)

    if level_id_text in levels:
        return levels[level_id_text]

    for key, value in levels.items():
        if str(key) == level_id_text:
            return value

    return None


def _build_rubric_evidence(
    assignment_context: dict,
    criterion_mapping: dict | None = None,
) -> list[dict]:
    """
    Converts rubric fillings into AI-friendly evidence.

    criterion_mapping is optional. If provided, it can enrich criterion IDs
    with Moodle competency details, criterion titles, max scores, and selected
    scores.
    """

    rubric_fillings = (
        assignment_context
        .get("rubric", {})
        .get("rubric_fillings", [])
    )

    evidence = []

    for filling in rubric_fillings:
        criterion_id = filling.get("criterion_id")
        level_id = filling.get("level_id")
        remark = filling.get("remark")

        mapping = {}

        if criterion_mapping:
            # Moodle may return criterion IDs as ints in one endpoint and
            # strings in another. Try both so the evidence mapper can use
            # stable string IDs without breaking older temporary mappings.
            mapping = (
                criterion_mapping.get(criterion_id)
                or criterion_mapping.get(str(criterion_id))
                or {}
            )

        levels = mapping.get("levels", {})
        selected_score = _lookup_level_score(levels, level_id)
        max_score = mapping.get("max_score")

        score_percent = None

        if selected_score is not None and max_score:
            score_percent = round((selected_score / max_score) * 100, 2)

        evidence.append(
            {
                "criterion_id": criterion_id,
                "criterion_title": mapping.get("title"),
                "competency_id": mapping.get("competency_id"),
                "competency_code": mapping.get("competency_code"),
                "competency_name": mapping.get("competency_name"),
                "silo_id": mapping.get("silo_id"),
                "silo_description": mapping.get("silo_description"),
                "mapping_source": mapping.get("mapping_source"),
                "selected_level_id": level_id,
                "selected_score": selected_score,
                "max_score": max_score,
                "score_percent": score_percent,
                "marker_remark": remark,
            }
        )

    return evidence


def _infer_weak_topics(
    assignment_context: dict,
    rubric_evidence: list[dict],
    weak_score_threshold: float = 70.0,
) -> list[dict]:
    """
    Identifies likely weak areas from grade, rubric scores, and feedback.

    This gives the AI a clear list of weak topics to target.
    """

    weak_topics = []

    grade_percent = (
        assignment_context
        .get("grading", {})
        .get("grade_percent")
    )

    if grade_percent is not None and grade_percent < weak_score_threshold:
        weak_topics.append(
            {
                "title": "Overall assignment performance",
                "evidence": f"The student received {grade_percent}% for this assignment.",
                "source": "grade",
            }
        )

    for item in rubric_evidence:
        score_percent = item.get("score_percent")
        marker_remark = item.get("marker_remark")

        is_weak_by_score = (
            score_percent is not None
            and score_percent < weak_score_threshold
        )

        is_weak_by_remark = (
            score_percent is None
            and _contains_improvement_signal(marker_remark)
        )

        if is_weak_by_score or is_weak_by_remark:
            weak_topics.append(
                {
                    "title": item.get("criterion_title")
                    or item.get("competency_name")
                    or item.get("silo_description")
                    or f"Rubric criterion {item.get('criterion_id')}",
                    "competency_id": item.get("competency_id"),
                    "competency_code": item.get("competency_code"),
                    "silo_id": item.get("silo_id"),
                    "score_percent": score_percent,
                    "evidence": marker_remark,
                    "source": "rubric",
                }
            )

    feedback_comment = (
        assignment_context
        .get("feedback", {})
        .get("comment")
    )

    if _contains_improvement_signal(feedback_comment):
        weak_topics.append(
            {
                "title": "Teacher feedback",
                "evidence": feedback_comment,
                "source": "feedback_comment",
            }
        )

    return weak_topics


def build_assignment_ai_input(
    assignment_context: dict,
    student_name: str | None = None,
    course_name: str | None = None,
    criterion_mapping: dict | None = None,
) -> dict:
    """
    Converts normalised Moodle assignment context into clean AI input.

    This is the main function the AI layer should receive for assignment-based
    feedback generation.

    It intentionally removes unnecessary Moodle metadata and keeps only
    learning-relevant evidence.
    """

    rubric_evidence = _build_rubric_evidence(
        assignment_context=assignment_context,
        criterion_mapping=criterion_mapping,
    )

    weak_topics = _infer_weak_topics(
        assignment_context=assignment_context,
        rubric_evidence=rubric_evidence,
    )

    grading = assignment_context.get("grading", {})
    submission = assignment_context.get("submission", {})
    feedback = assignment_context.get("feedback", {})

    return {
        "source": "moodle",
        "data_type": "assignment_learning_evidence",

        "student": {
            "moodle_user_id": assignment_context.get("student_user_id"),
            "name": student_name,
        },

        "course": {
            "course_id": assignment_context.get("course_id"),
            "course_name": course_name,
        },

        "assessment": {
            "assessment_type": "assignment",
            "assignment_id": assignment_context.get("assignment_id"),
            "course_module_id": assignment_context.get("course_module_id"),
            "name": assignment_context.get("assignment_name"),
            "max_grade": assignment_context.get("assignment_max_grade"),
            "task": assignment_context.get("assignment_task"),
        },

        "submission": {
            "submission_id": submission.get("submission_id"),
            "attempt_number": submission.get("attempt_number"),
            "status": submission.get("status"),
            "latest": submission.get("latest"),
            "submitted_files": _summarise_submitted_files(assignment_context),
        },

        "performance": {
            "is_graded": grading.get("is_graded"),
            "grading_status": grading.get("grading_status"),
            "grade_percent": grading.get("grade_percent"),
            "grade_display": grading.get("grade_display"),
        },

        "teacher_feedback": {
            "comment": feedback.get("comment"),
            "feedback_files": _summarise_feedback_files(assignment_context),
        },

        "rubric_evidence": rubric_evidence,

        "weak_topics": weak_topics,

        "ai_guidance": {
            "instruction": (
                "Use the grade, teacher feedback, rubric evidence, and weak topics "
                "to generate a student-friendly summary, areas for improvement, "
                "an evidence-based study plan, and MCQ questions."
            ),
            "do_not_do": [
                "Do not invent grades or rubric scores.",
                "Do not claim to have read the submitted PDF unless extracted text is provided.",
                "Base feedback only on the evidence provided in this object.",
            ],
        },
    }
