import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from services.report_orchestration_service import get_or_generate_learning_report


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
    Simulates the backend asking the AI component for a student report.
    """

    parser = argparse.ArgumentParser(
        description="Simulate backend get-or-generate learning report request."
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

    parser.add_argument(
        "--assignment-weight",
        type=float,
        default=100.0,
        help="How much this assignment contributes to mastery evidence.",
    )

    parser.add_argument(
        "--freshness-minutes",
        type=int,
        default=1440,
        help="Reuse an existing report if it was generated within this many minutes.",
    )

    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore existing reports and regenerate from Moodle/AI.",
    )

    parser.add_argument(
        "--mapping-file",
        help="Optional JSON file containing explicit criterion_id -> competency_id mappings.",
    )

    parser.add_argument(
        "--output",
        help="Optional path to save the orchestration response as JSON.",
    )

    parser.add_argument(
        "--show-report",
        action="store_true",
        help="Print the full report payload as well as the summary.",
    )

    return parser.parse_args()


def load_explicit_mappings(mapping_file: str | None) -> dict | list | None:
    """
    Loads optional explicit rubric criterion -> competency mappings.
    """

    if not mapping_file:
        return None

    return json.loads(Path(mapping_file).read_text(encoding="utf-8"))


args = parse_arguments()

with console.status(
    "[bold green]Handling backend-style learning report request...[/bold green]",
    spinner="dots",
):
    response = get_or_generate_learning_report(
        student_user_id=args.userid,
        course_id=args.courseid,
        assignment_id=args.assignmentid,
        student_name=args.studentname,
        course_name=args.coursename,
        assignment_weight_percent=args.assignment_weight,
        explicit_mappings=load_explicit_mappings(args.mapping_file),
        force_refresh=args.force_refresh,
        freshness_minutes=args.freshness_minutes,
    )


summary = {
    "status": response.get("status"),
    "source": response.get("source"),
    "job_id": response.get("job_id"),
    "learning_report_id": response.get("learning_report_id"),
    "student_id": response.get("student_id"),
    "report_key": response.get("report_key"),
    "overall_mastery_score": response.get("overall_mastery_score"),
    "generated_at": response.get("generated_at"),
    "error_message": response.get("error_message"),
}

display_json_panel(
    summary,
    "Backend Orchestration Response Summary",
)

if args.show_report:
    display_json_panel(
        response,
        "Full Backend Orchestration Response",
    )

if args.output:
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(response, indent=2),
        encoding="utf-8",
    )
    console.print(f"[green]Saved orchestration response to:[/green] {output_path.resolve()}")
