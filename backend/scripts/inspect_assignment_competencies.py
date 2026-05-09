import argparse
import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from config import get_settings
from moodle.client import MoodleClient
from moodle.evidence_mapper import normalise_competencies_from_moodle_response
from moodle.services.competencies import get_course_module_competencies


console = Console()
settings = get_settings()


def display_json_panel(data: dict | list | None, title: str) -> None:
    """
    Displays Moodle competency API output in a readable JSON panel.
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
    Allows assignment/activity competencies to be inspected by course module ID.
    """

    parser = argparse.ArgumentParser(
        description="Inspect Moodle competencies linked to an assignment activity."
    )

    parser.add_argument(
        "--cmid",
        type=int,
        required=True,
        help="Moodle course module ID for the assignment activity.",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show the raw Moodle competency response as well as the normalised summary.",
    )

    return parser.parse_args()


args = parse_arguments()

client = MoodleClient(
    base_url=settings.moodle_base_url,
    token=settings.moodle_token,
    rest_format=settings.moodle_rest_format,
)


competencies_response = get_course_module_competencies(
    client=client,
    course_module_id=args.cmid,
)

normalised_competencies = normalise_competencies_from_moodle_response(
    competencies_response
)

display_json_panel(
    [competency.__dict__ for competency in normalised_competencies],
    "Normalised Assignment Competencies",
)

if args.raw:
    display_json_panel(
        competencies_response,
        "Raw Course Module Competencies Response",
    )
