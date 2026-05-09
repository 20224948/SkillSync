import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from ai.provider_factory import get_ai_provider
from config import get_settings
from mastery.mastery_model import (
    calculate_mastery_report,
    mastery_report_to_dict,
)
from mastery.mock_data import get_mock_mastery_data


console = Console()
settings = get_settings()


def display_json_panel(data: dict | str, title: str) -> None:
    """
    Displays a dictionary or JSON string in a clean Rich panel.
    """

    # If data is a dictionary, convert it into formatted JSON.
    if isinstance(data, dict):
        json_string = json.dumps(data, indent=2)
    else:
        json_string = data

    # Add syntax highlighting so JSON is easier to read in the terminal.
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


# Load mock Moodle-style data from a separate file.
mock_data = get_mock_mastery_data() # Update to get moodle data - moodle_data = moodle_client.get_student_mastery_data(student_id, course_id)


# Calculate per-SILO and overall mastery using Python logic.
mastery_report = calculate_mastery_report(
    student_id=mock_data.student_id,
    course_id=mock_data.course_id,
    silos=mock_data.silos,
    assessments=mock_data.assessments,
    mappings=mock_data.mappings,
    results=mock_data.student_results,
)


# Display the calculated mastery report before sending it to the AI.
display_json_panel(
    mastery_report_to_dict(mastery_report),
    "Calculated Mastery Report",
)


# Prepare the mastery results in a format the AI can understand.
student_data_for_ai = {
    "student_id": mock_data.student_id,
    "student_name": mock_data.student_name,
    "course_id": mock_data.course_id,
    "course": mock_data.course_name,

    # This score is calculated by the Mastery Model, not invented by the AI.
    "overall_mastery_score": mastery_report.overall_mastery_score,

    # These are the weakest SILOs identified by the Mastery Model.
    "weak_topics": [
        {
            "silo_id": silo.silo_id,
            "title": silo.title,
            "mastery_score": silo.mastery_score,
            "confidence": silo.confidence,
            "evidence_count": silo.evidence_count,
        }
        for silo in mastery_report.weakest_silos
    ],

    # Full SILO breakdown gives the AI more context.
    "silo_mastery": [
        {
            "silo_id": silo.silo_id,
            "title": silo.title,
            "description": silo.description,
            "mastery_score": silo.mastery_score,
            "confidence": silo.confidence,
            "evidence_count": silo.evidence_count,
            "total_evidence_weight": silo.total_evidence_weight,
        }
        for silo in mastery_report.silo_mastery
    ],

    # Optional context that can later come from Moodle.
    "teacher_feedback": mock_data.teacher_feedback,
}


# Create the selected AI provider based on AI_PROVIDER in .env.
ai_provider = get_ai_provider()

with console.status(
    f"[bold green]Generating AI feedback using {settings.ai_provider}...[/bold green]",
    spinner="dots",
):
    feedback = ai_provider.generate_feedback(student_data_for_ai)


# Display the final AI response.
display_json_panel(
    feedback.model_dump_json(indent=2),
    "AI Feedback Based on Mastery Model",
)