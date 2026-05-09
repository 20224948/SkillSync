import json

import requests
from pydantic import ValidationError

from ai.base import AIProvider
from ai.prompts import SYSTEM_PROMPT
from ai.schemas import AIFeedback

# This connects Python to your local Qwen model through Ollama.
class OllamaProvider(AIProvider):
    """
    AI provider that sends requests to a local Ollama model.
    """

    def __init__(
        self,
        model_name: str = "qwen3.5:9b",
        base_url: str = "http://localhost:11434",
        timeout_seconds: int = 300,
    ):
        # Store these values so the model or Ollama URL can be changed later.
        self.model_name = model_name
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def generate_feedback(self, student_data: dict) -> AIFeedback:
        """
        Sends student data to Ollama and returns validated structured feedback.
        """

        user_prompt = (
            "Analyse the following student learning data.\n\n"
            f"{json.dumps(student_data, indent=2)}"
        )

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],

                # Forces Ollama to return output matching the Pydantic JSON schema.
                "format": AIFeedback.model_json_schema(),

                # Non-streaming is easier to validate and store in a database.
                "stream": False,

                # Lower temperature makes the output more consistent.
                "options": {
                    "temperature": 0.2,
                    # Controls the maximum number of tokens Ollama can generate.
                    # Increase this if structured JSON is being cut off.
                    "num_predict": 1800
                }
            },
            # 30 seconds to connect to Ollama, then self.timeout_seconds to wait for the model response.
            timeout=(30, self.timeout_seconds)
            
        )

        # Raise an error if the Ollama API request failed.
        response.raise_for_status()

        # Ollama returns the model response inside message.content.
        content = response.json()["message"]["content"]

        try:
            # Validate the AI response against our required structure.
            return AIFeedback.model_validate_json(content)

        except ValidationError as error:
            # This makes debugging easier if the model returns invalid JSON.
            raise ValueError(f"AI response did not match the required schema:\n{error}\n\nRaw response:\n{content}")
