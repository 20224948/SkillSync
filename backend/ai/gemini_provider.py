import json

from google import genai
from google.genai import types
from pydantic import ValidationError

from ai.base import AIProvider
from ai.prompts import SYSTEM_PROMPT
from ai.schemas import AIFeedback


class GeminiProvider(AIProvider):
    """
    AI provider that sends requests to the Gemini API.

    This provider returns the same AIFeedback structure as OllamaProvider,
    allowing the rest of the project to switch providers without changing logic.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        max_output_tokens: int = 4096,
        thinking_budget: int = 0,
    ):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing. Add it to your .env file.")

        # Store Gemini settings from .env.
        self.model_name = model_name
        self.max_output_tokens = max_output_tokens
        self.thinking_budget = thinking_budget

        # Create the Gemini client using the API key.
        self.client = genai.Client(api_key=api_key)

    def generate_feedback(self, student_data: dict) -> AIFeedback:
        """
        Send student data to Gemini and return validated structured feedback.
        """

        # Keep the student data separate from the system instructions.
        user_prompt = (
            "Analyse the following student learning data.\n\n"
            f"{json.dumps(student_data, indent=2)}"
        )

        # Base Gemini configuration.
        config = types.GenerateContentConfig(
            # Custom instructions from prompts.py.
            system_instruction=SYSTEM_PROMPT,

            # Tell Gemini to return JSON.
            response_mime_type="application/json",

            # Tell Gemini the exact JSON structure required.
            response_json_schema=AIFeedback.model_json_schema(),

            # Lower temperature makes the output more consistent.
            temperature=0.2,

            # Prevents the JSON from being cut off mid-response.
            max_output_tokens=self.max_output_tokens,
        )

        # Gemini 2.5 Flash supports disabling thinking with thinking_budget=0.
        # This can make responses faster and reduce token usage during testing.
        if self.model_name.startswith("gemini-2.5"):
            config.thinking_config = types.ThinkingConfig(
                thinking_budget=self.thinking_budget
            )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config,
        )

        try:
            # Validate Gemini's JSON response against the required Pydantic schema.
            return AIFeedback.model_validate_json(response.text)

        except ValidationError as error:
            raise ValueError(
                f"Gemini response did not match the required schema:\n{error}\n\n"
                f"Raw response:\n{response.text}"
            )
