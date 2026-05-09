from config import get_settings

from ai.base import AIProvider
from ai.ollama_provider import OllamaProvider
from ai.gemini_provider import GeminiProvider


def get_ai_provider() -> AIProvider:
    """
    Creates the correct AI provider based on AI_PROVIDER in the .env file.

    Supported values:
    - AI_PROVIDER=ollama
    - AI_PROVIDER=gemini
    """

    settings = get_settings()

    if settings.ai_provider == "ollama":
        return OllamaProvider(
            model_name=settings.ollama_model,
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_timeout_seconds,
        )

    if settings.ai_provider == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model,
            max_output_tokens=settings.gemini_max_output_tokens,
            thinking_budget=settings.gemini_thinking_budget,
        )

    raise ValueError(
        f"Unsupported AI_PROVIDER: {settings.ai_provider}. "
        "Use 'ollama' or 'gemini'."
    )