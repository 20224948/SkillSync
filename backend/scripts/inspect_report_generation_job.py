import argparse
import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from services.report_orchestration_service import get_report_generation_status


console = Console()


def display_json_panel(data: dict | list | str | None, title: str) -> None:
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
    Allows backend-style job status checks from the terminal.
    """

    parser = argparse.ArgumentParser(
        description="Inspect a SkillSync report generation job."
    )

    parser.add_argument(
        "--jobid",
        help="Supabase UUID for the report_generation_jobs row.",
    )

    parser.add_argument(
        "--userid",
        type=int,
        help="Moodle user ID for latest-job lookup.",
    )

    parser.add_argument(
        "--courseid",
        type=int,
        help="Moodle course ID for latest-job lookup.",
    )

    parser.add_argument(
        "--assignmentid",
        type=int,
        help="Moodle assignment ID / assignid for latest-job lookup.",
    )

    parser.add_argument(
        "--course-profile",
        action="store_true",
        help="Look up the latest course-level learning profile job.",
    )

    return parser.parse_args()


args = parse_arguments()

status = get_report_generation_status(
    job_id=args.jobid,
    student_user_id=args.userid,
    course_id=args.courseid,
    assignment_id=args.assignmentid,
    report_type=(
        "course_learning_profile"
        if args.course_profile
        else "assignment_learning_report"
    ),
)

display_json_panel(
    status,
    "Report Generation Job Status",
)
