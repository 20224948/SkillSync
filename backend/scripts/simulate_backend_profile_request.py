import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from services.report_orchestration_service import get_or_generate_student_learning_profile


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


def _parse_id_list(value: str | None) -> list[int] | None:
    if not value:
        return None

    return [
        int(item.strip())
        for item in value.split(",")
        if item.strip()
    ]


def _load_json_file(path: str | None) -> dict | list | None:
    if not path:
        return None

    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_arguments() -> argparse.Namespace:
    """
    Simulates the backend asking for a course-level learning profile.
    """

    parser = argparse.ArgumentParser(
        description="Simulate backend get-or-generate course profile request."
    )

    parser.add_argument("--userid", type=int, required=True)
    parser.add_argument("--courseid", type=int, required=True)
    parser.add_argument("--studentname", default=None)
    parser.add_argument("--coursename", default=None)
    parser.add_argument("--assignmentids")
    parser.add_argument("--quizids")
    parser.add_argument("--weights-file")
    parser.add_argument("--assignment-mapping-file")
    parser.add_argument("--quiz-mapping-file")
    parser.add_argument("--freshness-minutes", type=int, default=1440)
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--show-report", action="store_true")

    return parser.parse_args()


args = parse_arguments()

with console.status(
    "[bold green]Handling backend-style course profile request...[/bold green]",
    spinner="dots",
):
    response = get_or_generate_student_learning_profile(
        student_user_id=args.userid,
        course_id=args.courseid,
        student_name=args.studentname,
        course_name=args.coursename,
        assignment_ids=_parse_id_list(args.assignmentids),
        quiz_ids=_parse_id_list(args.quizids),
        assessment_weights=_load_json_file(args.weights_file),
        explicit_assignment_mappings=_load_json_file(args.assignment_mapping_file),
        explicit_quiz_mappings=_load_json_file(args.quiz_mapping_file),
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
    "Backend Course Profile Response Summary",
)

if args.show_report:
    display_json_panel(
        response,
        "Full Backend Course Profile Response",
    )

if args.output:
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(response, indent=2),
        encoding="utf-8",
    )
    console.print(f"[green]Saved orchestration response to:[/green] {output_path.resolve()}")
