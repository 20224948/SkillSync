import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from config import get_settings
from moodle.client import MoodleClient

# This file is ran via terminal by issuing the following command: python -m scripts.test_moodle_connection
console = Console()
settings = get_settings()


def display_json_panel(data: dict | list, title: str) -> None:
    """
    Displays Moodle JSON output in a readable terminal panel.
    """

    json_string = json.dumps(data, indent=2)

    json_output = Syntax(
        json_string,
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


client = MoodleClient(
    base_url=settings.moodle_base_url,
    token=settings.moodle_token,
    rest_format=settings.moodle_rest_format,
)

# First Moodle API test. This confirms the token, service, and REST setup work.
site_info = client.call("core_webservice_get_site_info")

display_json_panel(site_info, "Moodle API Connection Test")