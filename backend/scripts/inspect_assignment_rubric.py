import argparse
import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from config import get_settings
from moodle.client import MoodleClient
from moodle.services.rubrics import (
    get_grading_definitions,
    get_gradingform_instances,
    extract_definition_ids,
    summarise_grading_definitions,
    summarise_grading_instances,
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
    Allows the rubric to be inspected by course module ID.

    For Assignment 1: Report, your current known values are:
    - assignment_id / assignid = 1
    - course_module_id / cmid = 4
    """

    parser = argparse.ArgumentParser(
        description="Inspect Moodle assignment rubric / advanced grading data."
    )

    parser.add_argument(
        "--cmid",
        type=int,
        required=True,
        help="Moodle course module ID for the assignment activity.",
    )

    parser.add_argument(
        "--areaname",
        default="submissions",
        help="Moodle grading area name. For assignments this is usually 'submissions'.",
    )

    parser.add_argument(
        "--definitionid",
        type=int,
        help="Optional grading definition ID. If not provided, the script will fetch it from cmid.",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show full raw Moodle responses as well as summaries.",
    )

    return parser.parse_args()


args = parse_arguments()

client = MoodleClient(
    base_url=settings.moodle_base_url,
    token=settings.moodle_token,
    rest_format=settings.moodle_rest_format,
)


# Step 1: Get rubric / advanced grading definitions for the assignment cmid.
definitions_response = get_grading_definitions(
    client=client,
    course_module_id=args.cmid,
    area_name=args.areaname,
    active_only=1,
)

definition_summary = summarise_grading_definitions(definitions_response)

display_json_panel(
    definition_summary,
    "Rubric / Grading Definition Summary",
)


if args.raw:
    display_json_panel(
        definitions_response,
        "Raw Grading Definitions Response",
    )


# Step 2: Work out which grading definition ID to use.
if args.definitionid:
    definition_ids = [args.definitionid]
else:
    definition_ids = extract_definition_ids(definitions_response)


if not definition_ids:
    raise ValueError(
        "No grading definition IDs were found. "
        "Check that the assignment uses an advanced grading method such as rubric, "
        "and that the API user has permission to view grading data."
    )


# Step 3: Fetch grading form instances/fillings for each definition.
for definition_id in definition_ids:
    instances_response = get_gradingform_instances(
        client=client,
        definition_id=definition_id,
    )

    instance_summary = summarise_grading_instances(instances_response)

    display_json_panel(
        instance_summary,
        f"Grading Form Instance Summary - Definition {definition_id}",
    )

    if args.raw:
        display_json_panel(
            instances_response,
            f"Raw Grading Form Instances Response - Definition {definition_id}",
        )