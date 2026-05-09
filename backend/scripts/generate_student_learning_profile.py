import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from repositories.supabase_learning_reports import SupabaseLearningReportRepository
from services.learning_report_service import generate_student_learning_profile


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
    """
    Parses comma-separated Moodle IDs.
    """

    if not value:
        return None

    return [
        int(item.strip())
        for item in value.split(",")
        if item.strip()
    ]


def _load_json_file(path: str | None) -> dict | list | None:
    """
    Loads optional JSON configuration files.
    """

    if not path:
        return None

    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_arguments() -> argparse.Namespace:
    """
    Allows the course-level learning profile workflow to be run from terminal.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Generate a course-level SkillSync learning profile from Moodle "
            "assignment rubric evidence and quiz grade evidence."
        )
    )

    parser.add_argument("--userid", type=int, required=True)
    parser.add_argument("--courseid", type=int, required=True)
    parser.add_argument("--studentname", default=None)
    parser.add_argument("--coursename", default=None)
    parser.add_argument(
        "--assignmentids",
        help="Optional comma-separated assignment IDs. Defaults to all course assignments.",
    )
    parser.add_argument(
        "--quizids",
        help="Optional comma-separated quiz IDs. Defaults to all course quizzes.",
    )
    parser.add_argument(
        "--weights-file",
        help="Optional JSON file with assignment/quiz weights.",
    )
    parser.add_argument(
        "--assignment-mapping-file",
        help="Optional JSON file with explicit assignment criterion mappings.",
    )
    parser.add_argument(
        "--quiz-mapping-file",
        help="Optional JSON file with explicit quiz competency mappings.",
    )
    parser.add_argument("--output", help="Optional path to save the profile JSON.")
    parser.add_argument(
        "--save-to-supabase",
        action="store_true",
        help="Save the final profile into Supabase after generating it.",
    )

    return parser.parse_args()


args = parse_arguments()

with console.status(
    "[bold green]Generating SkillSync course learning profile...[/bold green]",
    spinner="dots",
):
    profile = generate_student_learning_profile(
        student_user_id=args.userid,
        course_id=args.courseid,
        student_name=args.studentname,
        course_name=args.coursename,
        assignment_ids=_parse_id_list(args.assignmentids),
        quiz_ids=_parse_id_list(args.quizids),
        assessment_weights=_load_json_file(args.weights_file),
        explicit_assignment_mappings=_load_json_file(args.assignment_mapping_file),
        explicit_quiz_mappings=_load_json_file(args.quiz_mapping_file),
    )


save_result = None

if args.save_to_supabase:
    with console.status(
        "[bold green]Saving course learning profile to Supabase...[/bold green]",
        spinner="dots",
    ):
        repository = SupabaseLearningReportRepository()
        save_result = repository.save_learning_report(profile)


if args.output:
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(profile, indent=2),
        encoding="utf-8",
    )


display_json_panel(
    {
        "report_key": profile["report_key"],
        "generated_at": profile["generated_at"],
        "overall_mastery_score": (
            profile.get("mastery_report", {})
            .get("overall_mastery_score")
        ),
        "included_assessments": profile.get("included_assessments", []),
        "skipped_assessments": profile.get("skipped_assessments", []),
        "ai_provider": profile.get("metadata", {}).get("ai_provider"),
        "ai_model": profile.get("metadata", {}).get("ai_model"),
    },
    "Course Learning Profile Summary",
)

display_json_panel(
    profile["mastery_report"],
    "Calculated Course Mastery Report",
)

if save_result:
    display_json_panel(
        save_result,
        "Supabase Save Result",
    )

if args.output:
    console.print(f"[green]Saved JSON profile to:[/green] {Path(args.output).resolve()}")
