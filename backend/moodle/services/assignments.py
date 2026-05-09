from moodle.client import MoodleClient


def get_assignments_by_course(
    client: MoodleClient,
    course_id: int,
) -> dict:
    """
    Gets assignment activities for a Moodle course.

    Moodle returns assignments grouped by course.
    """

    return client.call(
        "mod_assign_get_assignments",
        {
            "courseids[0]": course_id,
        },
    )


def summarise_assignments(assignments_response: dict) -> list[dict]:
    """
    Extracts the most useful assignment fields from Moodle's raw response.

    This makes the terminal output easier to read while still keeping
    the full raw response available if needed.
    """

    summary = []

    for course in assignments_response.get("courses", []):
        for assignment in course.get("assignments", []):
            summary.append(
                {
                    "course_id": course.get("id"),
                    "course_fullname": course.get("fullname"),
                    "assignment_id": assignment.get("id"),
                    "course_module_id": assignment.get("cmid"),
                    "name": assignment.get("name"),
                    "intro": assignment.get("intro"),
                    "grade": assignment.get("grade"),
                    "duedate": assignment.get("duedate"),
                    "allowsubmissionsfromdate": assignment.get("allowsubmissionsfromdate"),
                    "cutoffdate": assignment.get("cutoffdate"),
                    "submissiondrafts": assignment.get("submissiondrafts"),
                    "sendnotifications": assignment.get("sendnotifications"),
                    "submissionplugins": [
                        plugin.get("type")
                        for plugin in assignment.get("configs", [])
                        if plugin.get("plugin") == "file" or plugin.get("plugin") == "onlinetext"
                    ],
                }
            )

    return summary
def get_assignment_submission_status(
    client: MoodleClient,
    assignment_id: int,
    user_id: int,
) -> dict:
    """
    Gets a specific student's submission status for one Moodle assignment.

    This should return information such as:
    - whether the student submitted
    - submitted files
    - grading status
    - feedback comments if available
    """

    return client.call(
        "mod_assign_get_submission_status",
        {
            "assignid": assignment_id,
            "userid": user_id,
        },
    )


def get_assignment_grades(
    client: MoodleClient,
    assignment_id: int,
) -> dict:
    """
    Gets grade records for one Moodle assignment.

    Moodle returns grades for the assignment, so the script can later
    filter the result to a specific student.
    """

    return client.call(
        "mod_assign_get_grades",
        {
            "assignmentids[0]": assignment_id,
        },
    )


def find_student_grade(
    grades_response: dict,
    user_id: int,
) -> dict | None:
    """
    Finds one student's grade inside the Moodle assignment grades response.
    """

    for assignment in grades_response.get("assignments", []):
        for grade in assignment.get("grades", []):
            if grade.get("userid") == user_id:
                return grade

    return None

def find_assignment_by_id(
    assignments_response: dict,
    assignment_id: int,
) -> dict | None:
    """
    Finds a specific assignment from mod_assign_get_assignments output.
    """

    for course in assignments_response.get("courses", []):
        for assignment in course.get("assignments", []):
            if assignment.get("id") == assignment_id:
                return assignment

    return None


def get_assignment_cmid(
    client: MoodleClient,
    course_id: int,
    assignment_id: int,
) -> int:
    """
    Gets the course module ID / cmid for a specific Moodle assignment.

    The cmid is needed for rubric and competency API calls.
    """

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

    cmid = assignment.get("cmid")

    if cmid is None:
        raise ValueError(
            f"Assignment {assignment_id} was found, but no cmid was returned."
        )

    return int(cmid)