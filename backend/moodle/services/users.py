from moodle.client import MoodleClient


def get_user_by_field(
    client: MoodleClient,
    field: str,
    value: str,
) -> dict | None:
    """
    Finds a Moodle user by a supported field such as email, username, id, or idnumber.

    Returns the first matching user, or None if no user is found.
    """

    users = client.call(
        "core_user_get_users_by_field",
        {
            "field": field,
            "values[0]": value,
        },
    )

    if not users:
        return None

    return users[0]


def get_user_courses(
    client: MoodleClient,
    user_id: int,
) -> list:
    """
    Gets all Moodle courses that a user is enrolled in.
    """

    return client.call(
        "core_enrol_get_users_courses",
        {
            "userid": user_id,
        },
    )