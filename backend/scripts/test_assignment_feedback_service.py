import argparse
import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from services.assignment_feedback_service import generate_assignment_feedback_for_student


console = Console()


def display_json_panel(data: dict | list | str, title: str) -> None:
    """
    Displays JSON data in a readable Rich panel.
    """

    if isinstance(data, str):
        json_string = data
    else:
        json_string = json.dumps(data, indent=2)

    json_output = Syntax(
        json_string,
        "json",
        theme="github-dark",
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
    Allows the student/course/assignment values to be passed in from the terminal.
    """

    parser = argparse.ArgumentParser(
        description="Test the full SkillSync assignment feedback service."
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

    parser.add_argument(
        "--studentname",
        default=None,
        help="Optional student display name.",
    )

    parser.add_argument(
        "--coursename",
        default=None,
        help="Optional course display name.",
    )

    return parser.parse_args()


args = parse_arguments()


with console.status(
    "[bold green]Generating assignment feedback through service wrapper...[/bold green]",
    spinner="dots",
):
    result = generate_assignment_feedback_for_student(
        student_user_id=args.userid,
        course_id=args.courseid,
        assignment_id=args.assignmentid,
        student_name=args.studentname,
        course_name=args.coursename,
    )


display_json_panel(
    result["assignment_context"],
    "Assignment Context",
)

display_json_panel(
    result["ai_input"],
    "AI Input",
)

display_json_panel(
    result["ai_feedback"],
    "AI Feedback",
)