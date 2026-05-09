import argparse
import json
import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from config import get_settings
from moodle.client import MoodleClient
from moodle.evidence_mapper import (
    build_ai_criterion_mapping_from_moodle,
    build_student_rubric_evidence,
    student_rubric_evidence_to_dicts,
)
from moodle.normalisers.assignment_normaliser import build_student_assignment_context
from moodle.normalisers.ai_input_builder import build_assignment_ai_input
from moodle.normalisers.mastery_input_builder import (
    build_mastery_inputs_from_assignment_ai_input,
)
from mastery.mastery_model import calculate_mastery_report, mastery_report_to_dict

# test run via: python -m scripts.test_mastery_from_assignment_ai_input --userid 9 --courseid 2 --assignmentid 1 --studentname Susan --coursename "Introduction to IT" --assignment-weight 40
# or: python -m scripts.test_mastery_from_assignment_ai_input --userid 9 --courseid 2 --assignmentid 1 --studentname Susan --coursename "Introduction to IT" --assignment-weight 40

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
    Allows Moodle test values to be passed from the terminal.
    """

    parser = argparse.ArgumentParser(
        description="Calculate Mastery Model scores from Moodle assignment rubric evidence."
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
        help=(
            "How much this assignment contributes to mastery evidence. "
            "Use 100 for testing one assignment by itself."
        ),
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

    This is a placeholder for Baqir's backend/database later. During local
    testing, a small JSON file can stand in for that table.
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


# Step 1: Build the normalised Moodle assignment context.
assignment_context = build_student_assignment_context(
    client=client,
    student_user_id=args.userid,
    course_id=args.courseid,
    assignment_id=args.assignmentid,
)


# Step 2: Build the Moodle-backed rubric criterion -> competency mapping.
# The explicit mapping file has first priority. If it is not provided, the
# mapper uses the IT101 SILO code fallback, e.g. criterion "SILO 1" ->
# competency "IT101-SILO1". Missing/ambiguous mappings are logged as warnings.
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


# Step 3: Convert assignment context into AI-ready input.
# The AI receives evidence that has already been mapped to competencies; it does
# not infer mastery or decide which rubric criterion belongs to which SILO.
ai_input = build_assignment_ai_input(
    assignment_context=assignment_context,
    student_name=args.studentname,
    course_name=args.coursename,
    criterion_mapping=criterion_mapping,
)


# Step 4: Convert AI input into Mastery Model input objects.
mastery_inputs = build_mastery_inputs_from_assignment_ai_input(
    ai_input=ai_input,
    assignment_weight_percent=args.assignment_weight,
)


# Step 5: Calculate the student's mastery report.
mastery_report = calculate_mastery_report(
    student_id=mastery_inputs.student_id,
    course_id=mastery_inputs.course_id,
    silos=mastery_inputs.silos,
    assessments=mastery_inputs.assessments,
    mappings=mastery_inputs.mappings,
    results=mastery_inputs.student_results,
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
    "AI Input Used for Mastery Calculation",
)

display_json_panel(
    {
        "student_id": mastery_inputs.student_id,
        "course_id": mastery_inputs.course_id,
        "silos": [silo.__dict__ for silo in mastery_inputs.silos],
        "assessments": [assessment.__dict__ for assessment in mastery_inputs.assessments],
        "mappings": [mapping.__dict__ for mapping in mastery_inputs.mappings],
        "student_results": [result.__dict__ for result in mastery_inputs.student_results],
    },
    "Converted Mastery Model Inputs",
)

display_json_panel(
    mastery_report_to_dict(mastery_report),
    "Calculated Mastery Report From Moodle Assignment",
)
