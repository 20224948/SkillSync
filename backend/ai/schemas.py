from typing import Literal
from pydantic import BaseModel, Field


class FeedbackPoint(BaseModel):
    """
    Represents a brief area where the student needs improvement.
    """

    title: str = Field(
        description="Short title for the improvement area"
    )

    details: str = Field(
        description="Brief explanation of why this area needs improvement"
    )


class StudyPlanStep(BaseModel):
    """
    Represents one practical step in the student's study plan.
    """

    step_number: int = Field(
        description="The order this step should be completed in"
    )

    task: str = Field(
        description="The specific study task the student should complete"
    )

    method: str = Field(
        description="How the student should complete this task"
    )

    rationale: str = Field(
        description="Why this task will help the student improve"
    )

    estimated_time_minutes: int = Field(
        description="Estimated time required to complete this step"
    )


class EvidenceBasedStudyPlan(BaseModel):
    """
    Represents a targeted study plan for one weak learning area.
    """

    weak_area: str = Field(
        description="The specific weak topic or skill being addressed"
    )

    evidence: str = Field(
        description="The student data that supports why this weak area was identified"
    )

    learning_goal: str = Field(
        description="The outcome the student should aim to achieve"
    )

    priority: Literal["low", "medium", "high"] = Field(
        description="How urgently this area should be addressed"
    )

    study_steps: list[StudyPlanStep] = Field(
        description="Ordered study steps for improving this weak area"
    )

    success_measure: str = Field(
        description="How the student can tell they have improved"
    )


class MultipleChoiceQuestion(BaseModel):
    """
    Represents one generated multiple-choice question.
    """

    question: str = Field(
        description="The multiple-choice question being asked"
    )

    choice_1: str = Field(
        description="First possible answer"
    )

    choice_2: str = Field(
        description="Second possible answer"
    )

    choice_3: str = Field(
        description="Third possible answer"
    )

    correct_answer: str = Field(
        description="The correct answer. This must exactly match one of the choices"
    )

    explanation: str = Field(
        description="Brief explanation of why the correct answer is correct"
    )


class WeakAreaQuiz(BaseModel):
    """
    Represents generated MCQ questions for one weak area.
    """

    weak_area: str = Field(
        description="The weak area these questions are based on"
    )

    questions: list[MultipleChoiceQuestion] = Field(
        description="Two to three multiple-choice questions for this weak area"
    )


class LearningRecommendation(BaseModel):
    """
    Represents one practical recommendation linked to the student's evidence.
    """

    title: str = Field(
        description="Short title for the recommendation"
    )

    related_area: str = Field(
        description="The SILO, competency, or weak area this recommendation supports"
    )

    reason: str = Field(
        description="Evidence-based reason this recommendation is useful"
    )

    action: str = Field(
        description="Concrete action the student should take"
    )


class AIFeedback(BaseModel):
    """
    Final structured AI feedback returned by the model.
    """

    summary: str = Field(
        description="Somewhat detailed summary of the student's current learning progress"
    )

    areas_for_improvement: list[FeedbackPoint] = Field(
        description="Brief list of the student's main weak areas"
    )

    evidence_based_study_plan: list[EvidenceBasedStudyPlan] = Field(
        description="Targeted study plans based on the student's weak areas and available evidence"
    )

    generated_quiz_questions: list[WeakAreaQuiz] = Field(
        description="Generated multiple-choice quiz questions based on each weak area"
    )

    recommendations: list[LearningRecommendation] = Field(
        default_factory=list,
        description="Evidence-based learning recommendations linked to the student's weak areas"
    )
