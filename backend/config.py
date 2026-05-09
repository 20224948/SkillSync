import os
from dataclasses import dataclass

from dotenv import load_dotenv


# Loads values from the .env file into the Python environment.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """
    Central place for project settings.

    This keeps provider settings out of the main application code and allows
    us to switch between Ollama and Gemini by changing the .env file.
    """
    
    ai_provider: str = os.getenv("AI_PROVIDER", "ollama").lower()

    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))

    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_max_output_tokens: int = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "4096"))
    gemini_thinking_budget: int = int(os.getenv("GEMINI_THINKING_BUDGET", "0"))

    moodle_base_url: str | None = os.getenv("MOODLE_BASE_URL")
    moodle_token: str | None = os.getenv("MOODLE_TOKEN")
    moodle_rest_format: str = os.getenv("MOODLE_REST_FORMAT", "json")

    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    cors_allowed_origins: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")
    api_default_freshness_minutes: int = int(
        os.getenv("API_DEFAULT_FRESHNESS_MINUTES", "1440")
    )


def get_settings() -> Settings:
    """
    Return application settings.
    """
    return Settings()
