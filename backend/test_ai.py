from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from ai.provider_factory import get_ai_provider
from config import get_settings


console = Console()
settings = get_settings()


student_data = {
    "student_id": "s1001",
    "student_name": "Alex",
    "course_id": "net101",
    "course": "Networking Fundamentals",
    "quiz_average": 55,
    "weak_topics": ["OSPF", "subnetting", "ACLs"],
    "late_submissions": 2,
    "teacher_feedback": "Needs stronger explanation of routing concepts."
}


# Creates either OllamaProvider or GeminiProvider based on .env.
ai_provider = get_ai_provider()

with console.status(
    f"[bold green]Generating AI feedback using {settings.ai_provider}...[/bold green]",
    spinner="dots"
):
    feedback = ai_provider.generate_feedback(student_data)

# Convert the validated Pydantic object into JSON for database/frontend use.
feedback_json = feedback.model_dump_json(indent=2)

# Add JSON syntax highlighting so the terminal output is easier to read.
json_output = Syntax(
    feedback_json,
    "json",
    theme="one-dark",          # Dark modern syntax theme
    line_numbers=True,        # Shows line numbers for easier debugging
    word_wrap=True,           # Prevents long lines from running off-screen
    background_color="default" # Uses your terminal's dark background
)

console.print(Panel(json_output, title="Structured SkillSync AI Feedback"))