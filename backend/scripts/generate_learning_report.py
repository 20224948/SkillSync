import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from repositories.supabase_learning_reports import SupabaseLearningReportRepository
from services.learning_report_service import generate_learning_report_for_assignment


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
    Allows the end-to-end learning report workflow to be run from the terminal.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Generate a complete SkillSync learning report from live Moodle "
            "data, AI feedback, and optional Supabase storage."
        )
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
        "--mapping-file",
        help=(
            "Optional JSON file containing explicit criterion_id -> competency_id "
            "mappings. If omitted, the code falls back to SILO code matching."
        ),
    )

    parser.add_argument(
        "--output",
        help="Optional path to save the final learning report as JSON.",
    )

    parser.add_argument(
        "--save-to-supabase",
        action="store_true",
        help="Save the final report into Supabase after generating it.",
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
    "[bold green]Generating SkillSync learning report...[/bold green]",
    spinner="dots",
):
    learning_report = generate_learning_report_for_assignment(
        student_user_id=args.userid,
        course_id=args.courseid,
        assignment_id=args.assignmentid,
        student_name=args.studentname,
        course_name=args.coursename,
        assignment_weight_percent=args.assignment_weight,
        explicit_mappings=load_explicit_mappings(args.mapping_file),
    )


save_result = None

if args.save_to_supabase:
    with console.status(
        "[bold green]Saving learning report to Supabase...[/bold green]",
        spinner="dots",
    ):
        repository = SupabaseLearningReportRepository()
        save_result = repository.save_learning_report(learning_report)


if args.output:
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(learning_report, indent=2),
        encoding="utf-8",
    )


display_json_panel(
    {
        "report_key": learning_report["report_key"],
        "generated_at": learning_report["generated_at"],
        "overall_mastery_score": (
            learning_report.get("mastery_report", {})
            .get("overall_mastery_score")
        ),
        "calculated_weak_areas": learning_report.get("calculated_weak_areas", []),
        "ai_provider": learning_report.get("metadata", {}).get("ai_provider"),
        "ai_model": learning_report.get("metadata", {}).get("ai_model"),
    },
    "Learning Report Summary",
)

display_json_panel(
    learning_report["mastery_report"],
    "Calculated Mastery Report",
)

display_json_panel(
    learning_report["ai_feedback"],
    "AI Feedback / Study Plan / MCQs / Recommendations",
)

if save_result:
    display_json_panel(
        save_result,
        "Supabase Save Result",
    )

if args.output:
    console.print(f"[green]Saved JSON report to:[/green] {Path(args.output).resolve()}")
