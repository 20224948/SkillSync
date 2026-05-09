from moodle.client import MoodleClient


def _call_required_competency_function(
    client: MoodleClient,
    function_name: str,
    params: dict,
) -> dict | list:
    """
    Calls a Moodle competency web service function with a clearer error message.

    Moodle sites do not always enable every external service by default. When one
    of these calls fails, the project should tell the Moodle/backend team exactly
    which function is needed instead of failing with a vague API error.
    """

    try:
        return client.call(function_name, params)
    except RuntimeError as error:
        raise RuntimeError(
            f"Moodle external function '{function_name}' is required for "
            "competency/rubric mapping. Enable it for the web service user, "
            f"then try again. Original Moodle error: {error}"
        ) from error


def get_course_competencies(
    client: MoodleClient,
    course_id: int,
) -> dict | list:
    """
    Gets competencies attached to a Moodle course.

    This is useful for inspection and development, but assignment evidence should
    normally use get_course_module_competencies() so the mapper only considers
    competencies linked to the activity being graded.
    """

    return _call_required_competency_function(
        client=client,
        function_name="core_competency_list_course_competencies",
        params={"courseid": course_id},
    )


def get_course_module_competencies(
    client: MoodleClient,
    course_module_id: int,
) -> dict | list:
    """
    Gets competencies attached to a specific Moodle activity/course module.

    For Assignment 1 this should return the competencies linked to that
    assignment activity. The mapper then connects individual rubric criteria to
    these allowed competencies.
    """

    return _call_required_competency_function(
        client=client,
        function_name="core_competency_list_course_module_competencies",
        params={"cmid": course_module_id},
    )
