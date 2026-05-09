import html
import re
from typing import Any

from moodle.client import MoodleClient
from moodle.services.assignments import (
    get_assignments_by_course,
    find_assignment_by_id,
    get_assignment_submission_status,
    get_assignment_grades,
    find_student_grade,
    get_assignment_cmid,
)
from moodle.services.rubrics import (
    get_grading_definitions,
    extract_definition_ids,
    get_gradingform_instances,
    find_rubric_instance_for_grade,
)


def clean_html_text(value: str | None) -> str:
    """
    Converts Moodle HTML fields into cleaner plain text.

    Moodle often returns assignment tasks and feedback comments as HTML,
    so this removes tags and decodes HTML entities.
    """

    if not value:
        return ""

    # Preserve paragraph and line break separation before removing tags.
    value = re.sub(r"</p\s*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)

    # Remove all remaining HTML tags.
    value = re.sub(r"<[^>]+>", "", value)

    # Decode HTML entities such as &nbsp; and &amp;.
    value = html.unescape(value)

    # Clean up excessive spacing while keeping readable line breaks.
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n\s*\n+", "\n", value)

    return value.strip()


def parse_moodle_grade(value: Any) -> float | None:
    """
    Converts Moodle grade values into a float.

    Moodle uses -1.00000 to represent an ungraded submission,
    so this returns None for negative grades.
    """

    if value is None:
        return None

    try:
        grade = float(value)
    except (TypeError, ValueError):
        return None

    if grade < 0:
        return None

    return grade


def extract_submission_files(submission_status: dict) -> list[dict]:
    """
    Extracts submitted files from mod_assign_get_submission_status output.

    For file submissions, Moodle stores the submitted PDF inside:
    lastattempt -> submission -> plugins -> fileareas -> files
    """

    files: list[dict] = []

    submission = (
        submission_status
        .get("lastattempt", {})
        .get("submission", {})
    )

    for plugin in submission.get("plugins", []):
        if plugin.get("type") != "file":
            continue

        for filearea in plugin.get("fileareas", []):
            if filearea.get("area") != "submission_files":
                continue

            for file in filearea.get("files", []):
                files.append(
                    {
                        "filename": file.get("filename"),
                        "filepath": file.get("filepath"),
                        "filesize": file.get("filesize"),
                        "fileurl": file.get("fileurl"),
                        "mimetype": file.get("mimetype"),
                        "timemodified": file.get("timemodified"),
                    }
                )

    return files


def extract_feedback_comment(submission_status: dict) -> str:
    """
    Extracts the teacher's feedback comment from the Moodle response.

    Feedback comments are usually stored inside:
    feedback -> plugins -> comments -> editorfields -> text
    """

    feedback = submission_status.get("feedback", {})

    for plugin in feedback.get("plugins", []):
        if plugin.get("type") != "comments":
            continue

        for field in plugin.get("editorfields", []):
            if field.get("name") == "comments":
                return clean_html_text(field.get("text"))

    return ""


def extract_feedback_files(submission_status: dict) -> list[dict]:
    """
    Extracts feedback files, such as annotated PDFs, from Moodle.

    This is separate from the student's submitted PDF.
    """

    files: list[dict] = []

    feedback = submission_status.get("feedback", {})

    for plugin in feedback.get("plugins", []):
        for filearea in plugin.get("fileareas", []):
            for file in filearea.get("files", []):
                files.append(
                    {
                        "plugin_type": plugin.get("type"),
                        "plugin_name": plugin.get("name"),
                        "area": filearea.get("area"),
                        "filename": file.get("filename"),
                        "filepath": file.get("filepath"),
                        "filesize": file.get("filesize"),
                        "fileurl": file.get("fileurl"),
                        "mimetype": file.get("mimetype"),
                        "timemodified": file.get("timemodified"),
                    }
                )

    return files


def extract_assignment_task(submission_status: dict, assignment: dict | None) -> str:
    """
    Extracts the assignment task/instructions.

    Prefer assignmentdata.activity from submission status, because it usually
    contains the task students see. Fall back to the assignment intro/activity.
    """

    assignment_data = submission_status.get("assignmentdata", {})
    task = assignment_data.get("activity")

    if task:
        return clean_html_text(task)

    if assignment:
        return clean_html_text(
            assignment.get("activity")
            or assignment.get("intro")
        )

    return ""


def normalise_rubric_instance(rubric_instance: dict | None) -> list[dict]:
    """
    Converts a matched Moodle rubric instance into a cleaner list of criterion results.

    This currently returns criterion_id, selected level_id, and marker remark.
    Later, we can enrich this with criterion names and level scores.
    """

    if not rubric_instance:
        return []

    rubric_results: list[dict] = []

    rubric = rubric_instance.get("rubric", {})

    for criterion in rubric.get("criteria", []):
        rubric_results.append(
            {
                "criterion_id": criterion.get("criterionid") or criterion.get("id"),
                "level_id": criterion.get("levelid"),
                "remark": clean_html_text(criterion.get("remark")),
                "remark_format": criterion.get("remarkformat"),
            }
        )

    return rubric_results


def get_student_rubric_fillings(
    client: MoodleClient,
    course_module_id: int,
    grade_id: int | None,
) -> list[dict]:
    """
    Gets the completed rubric fillings for the selected student's grade.

    Moodle links grading form instances to assignment grade records using itemid.
    For assignment rubrics:
    - student grade id usually matches rubric instance itemid
    """

    if grade_id is None:
        return []

    definitions_response = get_grading_definitions(
        client=client,
        course_module_id=course_module_id,
        area_name="submissions",
        active_only=1,
    )

    definition_ids = extract_definition_ids(definitions_response)

    if not definition_ids:
        return []

    for definition_id in definition_ids:
        instances_response = get_gradingform_instances(
            client=client,
            definition_id=definition_id,
        )

        rubric_instance = find_rubric_instance_for_grade(
            instances_response=instances_response,
            grade_id=grade_id,
        )

        if rubric_instance:
            return normalise_rubric_instance(rubric_instance)

    return []


def build_student_assignment_context(
    client: MoodleClient,
    student_user_id: int,
    course_id: int,
    assignment_id: int,
) -> dict:
    """
    Builds a clean assignment context object for one student and one assignment.

    This is the main normaliser function.

    It combines:
    - assignment task
    - submission status
    - submitted PDF files
    - grade
    - feedback comment
    - feedback files
    - rubric fillings

    The returned dictionary is much easier to pass into:
    - the AI model
    - the Mastery Model
    - the backend/database
    """

    # Get assignment metadata, including the course module ID / cmid.
    assignments_response = get_assignments_by_course(
        client=client,
        course_id=course_id,
    )

    assignment = find_assignment_by_id(
        assignments_response=assignments_response,
        assignment_id=assignment_id,
    )

    if assignment is None:
        raise ValueError(
            f"Could not find assignment_id={assignment_id} in course_id={course_id}."
        )

    course_module_id = assignment.get("cmid")

    if course_module_id is None:
        # Fallback helper in case the assignment object shape changes later.
        course_module_id = get_assignment_cmid(
            client=client,
            course_id=course_id,
            assignment_id=assignment_id,
        )

    course_module_id = int(course_module_id)

    # Get the student's submission status, task data, feedback, and files.
    submission_status = get_assignment_submission_status(
        client=client,
        assignment_id=assignment_id,
        user_id=student_user_id,
    )

    # Get the assignment grade list and find the selected student's grade.
    grades_response = get_assignment_grades(
        client=client,
        assignment_id=assignment_id,
    )

    student_grade = find_student_grade(
        grades_response=grades_response,
        user_id=student_user_id,
    )

    grade_id = student_grade.get("id") if student_grade else None

    # The feedback section often contains the most complete grade display.
    feedback = submission_status.get("feedback", {})
    feedback_grade = feedback.get("grade", {})

    grade_percent = parse_moodle_grade(
        feedback_grade.get("grade")
        or (student_grade or {}).get("grade")
    )

    rubric_fillings = get_student_rubric_fillings(
        client=client,
        course_module_id=course_module_id,
        grade_id=grade_id,
    )

    last_attempt = submission_status.get("lastattempt", {})
    submission = last_attempt.get("submission", {})

    return {
        "student_user_id": student_user_id,
        "course_id": course_id,
        "assignment_id": assignment_id,
        "course_module_id": course_module_id,

        "assignment_name": assignment.get("name"),
        "assignment_max_grade": parse_moodle_grade(assignment.get("grade")),
        "assignment_task": extract_assignment_task(
            submission_status=submission_status,
            assignment=assignment,
        ),

        "submission": {
            "submission_id": submission.get("id"),
            "attempt_number": submission.get("attemptnumber"),
            "status": submission.get("status"),
            "timecreated": submission.get("timecreated"),
            "timemodified": submission.get("timemodified"),
            "latest": submission.get("latest"),
            "submitted_files": extract_submission_files(submission_status),
        },

        "grading": {
            "is_graded": last_attempt.get("graded"),
            "grading_status": last_attempt.get("gradingstatus"),
            "grade_id": grade_id,
            "grade_percent": grade_percent,
            "grade_display": feedback.get("gradefordisplay"),
            "grader_user_id": feedback_grade.get("grader")
            or (student_grade or {}).get("grader"),
            "graded_date": feedback.get("gradeddate"),
        },

        "feedback": {
            "comment": extract_feedback_comment(submission_status),
            "feedback_files": extract_feedback_files(submission_status),
        },

        "rubric": {
            "rubric_fillings": rubric_fillings,
        },
    }