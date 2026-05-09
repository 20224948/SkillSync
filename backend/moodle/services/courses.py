from moodle.client import MoodleClient


def get_course_contents(
    client: MoodleClient,
    course_id: int,
) -> list:
    """
    Gets the full course structure, including sections and activities.

    This is useful for finding modules, assignments, resources, and files
    inside a Moodle course.
    """

    return client.call(
        "core_course_get_contents",
        {
            "courseid": course_id,
        },
    )


def get_course_by_id(
    client: MoodleClient,
    course_id: int,
) -> dict | None:
    """
    Gets basic course information for a specific course ID.
    """

    response = client.call(
        "core_course_get_courses_by_field",
        {
            "field": "id",
            "value": course_id,
        },
    )

    courses = response.get("courses", [])

    if not courses:
        return None

    return courses[0]