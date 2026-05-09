from abc import ABC, abstractmethod

from ai.schemas import AIFeedback

# This defines the shared interface all future AI providers must follow.

class AIProvider(ABC):
    """
    Base class for all AI providers.

    Every provider must return the same AIFeedback structure so the rest
    of the system does not care whether the model is Ollama or Gemini.
    """

    @abstractmethod
    def generate_feedback(self, student_data: dict) -> AIFeedback:
        """
        Generate structured personalised learning feedback from student data.
        """
        pass


