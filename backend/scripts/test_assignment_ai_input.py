import argparse
import json
import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from ai.provider_factory import get_ai_provider
from config import get_settings
from moodle.client import MoodleClient
from moodle.evidence_mapper import (
    build_ai_criterion_mapping_from_moodle,
    build_student_rubric_evidence,
    student_rubric_evidence_to_dicts,
)
from moodle.normalisers.assignment_normaliser import build_student_assignment_context
from moodle.normalisers.ai_input_builder import build_assignment_ai_input


console = Console()
settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


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
    Allows test values to be passed from the terminal.

    In production, these values will come from the backend/frontend.
    """

    parser = argparse.ArgumentParser(
        description="Build clean AI input from a Moodle assignment context."
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
        "--send-to-ai",
        action="store_true",
        help="Send the generated AI input to the selected AI provider.",
    )

    parser.add_argument(
        "--mapping-file",
        help=(
            "Optional JSON file containing explicit criterion_id -> competency_id "
            "mappings. If omitted, the script falls back to SILO code matching."
        ),
    )

    return parser.parse_args()


def load_explicit_mappings(mapping_file: str | None) -> dict | list | None:
    """
    Loads optional explicit rubric criterion -> competency mappings.

    This mirrors the future backend/database mapping table while keeping local
    testing simple.
    """

    if not mapping_file:
        return None

    return json.loads(Path(mapping_file).read_text(encoding="utf-8"))


args = parse_arguments()

client = MoodleClient(
    base_url=settings.moodle_base_url,
    token=settings.moodle_token,
    rest_format=settings.moodle_rest_format,
)


# Step 1: Build the clean normalised Moodle assignment context.
assignment_context = build_student_assignment_context(
    client=client,
    student_user_id=args.userid,
    course_id=args.courseid,
    assignment_id=args.assignmentid,
)


# Step 2: Resolve rubric criterion -> competency links from Moodle.
criterion_mapping = build_ai_criterion_mapping_from_moodle(
    client=client,
    course_module_id=assignment_context["course_module_id"],
    assignment_id=args.assignmentid,
    explicit_mappings=load_explicit_mappings(args.mapping_file),
)

student_competency_evidence = build_student_rubric_evidence(
    student_id=args.userid,
    assignment_id=args.assignmentid,
    rubric_fillings=assignment_context.get("rubric", {}).get("rubric_fillings", []),
    criterion_mapping=criterion_mapping,
)


# Step 3: Convert the normalised Moodle context into AI-ready input.
ai_input = build_assignment_ai_input(
    assignment_context=assignment_context,
    student_name=args.studentname,
    course_name=args.coursename,
    criterion_mapping=criterion_mapping,
)


display_json_panel(
    criterion_mapping,
    "Resolved Rubric Criterion To Competency Mapping",
)

display_json_panel(
    student_rubric_evidence_to_dicts(student_competency_evidence),
    "Normalised Student Competency Evidence",
)

display_json_panel(
    ai_input,
    "AI Input Built From Moodle Assignment Context",
)


# Step 3: Optional test - send this AI input into your existing AI provider.
if args.send_to_ai:
    ai_provider = get_ai_provider()

    with console.status(
        f"[bold green]Generating AI feedback using {settings.ai_provider}...[/bold green]",
        spinner="dots",
    ):
        feedback = ai_provider.generate_feedback(ai_input)

    display_json_panel(
        feedback.model_dump_json(indent=2),
        "AI Feedback Generated From Moodle Assignment Evidence",
    )
