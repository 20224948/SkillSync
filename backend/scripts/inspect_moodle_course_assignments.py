import argparse
import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from config import get_settings
from moodle.client import MoodleClient
from moodle.services.courses import get_course_by_id, get_course_contents
from moodle.services.assignments import (
    get_assignments_by_course,
    summarise_assignments,
)

# run via: python -m scripts.inspect_moodle_course_assignments --courseid 2
# Change course ID

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
    Allows the course ID to be selected from the terminal.
    """

    parser = argparse.ArgumentParser(
        description="Inspect a Moodle course and its assignments."
    )

    parser.add_argument(
        "--courseid",
        type=int,
        required=True,
        help="Moodle course ID to inspect.",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show the full raw Moodle assignment response.",
    )

    return parser.parse_args()


args = parse_arguments()

client = MoodleClient(
    base_url=settings.moodle_base_url,
    token=settings.moodle_token,
    rest_format=settings.moodle_rest_format,
)


# Step 1: Get basic course information.
course = get_course_by_id(
    client=client,
    course_id=args.courseid,
)

if course is None:
    raise ValueError(f"No Moodle course found with ID: {args.courseid}")

display_json_panel(
    course,
    "Moodle Course Details",
)


# Step 2: Get course structure.
# This shows sections and modules inside the course.
course_contents = get_course_contents(
    client=client,
    course_id=args.courseid,
)

display_json_panel(
    course_contents,
    "Moodle Course Contents",
)


# Step 3: Get assignment activities for this course.
assignments_response = get_assignments_by_course(
    client=client,
    course_id=args.courseid,
)

assignment_summary = summarise_assignments(assignments_response)

display_json_panel(
    assignment_summary,
    "Assignment Summary",
)


# Optional: show the full raw assignment response for debugging.
if args.raw:
    display_json_panel(
        assignments_response,
        "Raw Assignment Response",
    )