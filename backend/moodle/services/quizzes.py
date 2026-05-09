from moodle.client import MoodleClient


def get_quizzes_by_course(
    client: MoodleClient,
    course_id: int,
) -> dict:
    """
    Gets quiz activities for a Moodle course.
    """

    return client.call(
        "mod_quiz_get_quizzes_by_courses",
        {
            "courseids[0]": course_id,
        },
    )


def find_quiz_by_id(
    quizzes_response: dict,
    quiz_id: int,
) -> dict | None:
    """
    Finds a specific quiz from mod_quiz_get_quizzes_by_courses output.
    """

    for quiz in quizzes_response.get("quizzes", []):
        if quiz.get("id") == quiz_id:
            return quiz

    return None


def summarise_quizzes(quizzes_response: dict) -> list[dict]:
    """
    Extracts the most useful quiz fields from Moodle's raw response.
    """

    summary = []

    for quiz in quizzes_response.get("quizzes", []):
        summary.append(
            {
                "course_id": quiz.get("course"),
                "quiz_id": quiz.get("id"),
                "course_module_id": quiz.get("coursemodule"),
                "name": quiz.get("name"),
                "intro": quiz.get("intro"),
                "grade": quiz.get("grade"),
                "sumgrades": quiz.get("sumgrades"),
                "grademethod": quiz.get("grademethod"),
                "timeopen": quiz.get("timeopen"),
                "timeclose": quiz.get("timeclose"),
                "visible": quiz.get("visible"),
            }
        )

    return summary


def get_user_quiz_attempts(
    client: MoodleClient,
    quiz_id: int,
    user_id: int = 0,
    status: str = "all",
    include_previews: bool = False,
) -> dict:
    """
    Gets one user's attempts for a Moodle quiz.

    Moodle 5.x deprecates mod_quiz_get_user_attempts in favour of
    mod_quiz_get_user_quiz_attempts. Use this wrapper for all new code.
    """

    return client.call(
        "mod_quiz_get_user_quiz_attempts",
        {
            "quizid": quiz_id,
            "userid": user_id,
            "status": status,
            "includepreviews": int(include_previews),
        },
    )


def get_user_best_grade(
    client: MoodleClient,
    quiz_id: int,
    user_id: int,
) -> dict:
    """
    Gets the user's best/final grade for one Moodle quiz.
    """

    return client.call(
        "mod_quiz_get_user_best_grade",
        {
            "quizid": quiz_id,
            "userid": user_id,
        },
    )


def get_quiz_cmid(
    client: MoodleClient,
    course_id: int,
    quiz_id: int,
) -> int:
    """
    Gets the course module ID / cmid for a specific Moodle quiz.
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

    cmid = quiz.get("coursemodule")

    if cmid is None:
        raise ValueError(
            f"Quiz {quiz_id} was found, but no course module ID was returned."
        )

    return int(cmid)
