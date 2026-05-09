import argparse
import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from config import get_settings
from moodle.client import MoodleClient
from moodle.services.assignments import (
    get_assignment_submission_status,
    get_assignment_grades,
    find_student_grade,
)


console = Console()
settings = get_settings()


def display_json_panel(data: dict | list | None, title: str) -> None:
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
    Allows the student and assignment to be selected from the terminal.
    """

    parser = argparse.ArgumentParser(
        description="Inspect one student's Moodle assignment submission and grade."
    )

    parser.add_argument(
        "--userid",
        type=int,
        required=True,
        help="Moodle user ID for the student.",
    )

    parser.add_argument(
        "--assignmentid",
        type=int,
        required=True,
        help="Moodle assignment ID, also called assignid.",
    )

    return parser.parse_args()


args = parse_arguments()

client = MoodleClient(
    base_url=settings.moodle_base_url,
    token=settings.moodle_token,
    rest_format=settings.moodle_rest_format,
)


# Step 1: Get the student's submission status for the assignment.
submission_status = get_assignment_submission_status(
    client=client,
    assignment_id=args.assignmentid,
    user_id=args.userid,
)

display_json_panel(
    submission_status,
    "Student Assignment Submission Status",
)


# Step 2: Get assignment grades.
grades_response = get_assignment_grades(
    client=client,
    assignment_id=args.assignmentid,
)

display_json_panel(
    grades_response,
    "Raw Assignment Grades Response",
)


# Step 3: Extract the selected student's grade from the full grade response.
student_grade = find_student_grade(
    grades_response=grades_response,
    user_id=args.userid,
)

display_json_panel(
    student_grade,
    "Selected Student Grade",
)