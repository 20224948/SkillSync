import argparse
import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from config import get_settings
from moodle.client import MoodleClient
from moodle.normalisers.assignment_normaliser import build_student_assignment_context


console = Console()
settings = get_settings()


def display_json_panel(data: dict | list | None, title: str) -> None:
    """
    Displays normalised Moodle data in a readable JSON panel.
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
    Allows the student, course, and assignment to be selected from the terminal.

    This is still a test script. In production, these values will likely come
    from the backend/frontend instead of terminal arguments.
    """

    parser = argparse.ArgumentParser(
        description="Build a clean normalised Moodle assignment context."
    )

    parser.add_argument(
        "--userid",
        type=int,
        required=True,
        help="Moodle user ID for the student.",
    )

    parser.add_argument(
        "--courseid",
        type=int,
        required=True,
        help="Moodle course ID.",
    )

    parser.add_argument(
        "--assignmentid",
        type=int,
        required=True,
        help="Moodle assignment ID / assignid.",
    )

    return parser.parse_args()


args = parse_arguments()

client = MoodleClient(
    base_url=settings.moodle_base_url,
    token=settings.moodle_token,
    rest_format=settings.moodle_rest_format,
)


assignment_context = build_student_assignment_context(
    client=client,
    student_user_id=args.userid,
    course_id=args.courseid,
    assignment_id=args.assignmentid,
)

display_json_panel(
    assignment_context,
    "Normalised Student Assignment Context",
)