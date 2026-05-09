import argparse
import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from config import get_settings
from moodle.client import MoodleClient
from moodle.services.users import get_user_by_field, get_user_courses

# run script via one of these : 
# python -m scripts.inspect_moodle_users_courses --userid 3
# python -m scripts.inspect_moodle_users_courses --email john.smith@moodle.com
# python -m scripts.inspect_moodle_users_courses --username student1

console = Console()
settings = get_settings()


def display_json_panel(data: dict | list, title: str) -> None:
    """
    Displays Moodle API output in a readable JSON panel.
    """

    json_output = Syntax(
        json.dumps(data, indent=2),
        "json",
        theme="one-dark",
        line_numbers=True,
        word_wrap=True,
        background_color="default",
    )

    console.print(
        Panel(
            json_output,
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
        )
    )


def parse_arguments() -> argparse.Namespace:
    """
    Allows the student to be selected from the terminal instead of hardcoding it.
    """

    parser = argparse.ArgumentParser(
        description="Inspect a Moodle user's profile and enrolled courses."
    )

    student_selector = parser.add_mutually_exclusive_group(required=True)

    student_selector.add_argument(
        "--email",
        help="Find the Moodle user by email address.",
    )

    student_selector.add_argument(
        "--username",
        help="Find the Moodle user by Moodle username.",
    )

    student_selector.add_argument(
        "--idnumber",
        help="Find the Moodle user by Moodle ID number.",
    )

    student_selector.add_argument(
        "--userid",
        type=int,
        help="Use a known Moodle user ID directly.",
    )

    return parser.parse_args()


args = parse_arguments()

client = MoodleClient(
    base_url=settings.moodle_base_url,
    token=settings.moodle_token,
    rest_format=settings.moodle_rest_format,
)


# If a Moodle user ID is already known, use it directly.
if args.userid:
    student_id = args.userid
    display_json_panel(
        {"id": student_id},
        "Selected Moodle User ID",
    )

else:
    # Otherwise, look up the Moodle user by email, username, or idnumber.
    if args.email:
        field = "email"
        value = args.email
    elif args.username:
        field = "username"
        value = args.username
    else:
        field = "idnumber"
        value = args.idnumber

    student = get_user_by_field(
        client=client,
        field=field,
        value=value,
    )

    if student is None:
        raise ValueError(f"No Moodle user found using {field}: {value}")

    student_id = student["id"]

    display_json_panel(
        student,
        "Moodle User Lookup",
    )


# Get the student's enrolled Moodle courses.
courses = get_user_courses(
    client=client,
    user_id=student_id,
)

display_json_panel(
    courses,
    "Student Enrolled Courses",
)