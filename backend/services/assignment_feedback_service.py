from ai.provider_factory import get_ai_provider
from config import get_settings
from moodle.client import MoodleClient
from moodle.evidence_mapper import (
    build_ai_criterion_mapping_from_moodle,
    build_student_rubric_evidence,
    student_rubric_evidence_to_dicts,
)
from moodle.normalisers.assignment_normaliser import build_student_assignment_context
from moodle.normalisers.ai_input_builder import build_assignment_ai_input


def generate_assignment_feedback_for_student(
    student_user_id: int,
    course_id: int,
    assignment_id: int,
    student_name: str | None = None,
    course_name: str | None = None,
    explicit_mappings: dict | list | None = None,
) -> dict:
    """
    Runs the full assignment feedback workflow.

    This function:
    1. Connects to Moodle.
    2. Gets the student's assignment submission, grade, feedback, and rubric data.
    3. Resolves rubric criterion -> competency mappings from Moodle data.
    4. Converts the Moodle data into clean AI input.
    5. Sends the AI input to the selected AI provider.
    6. Returns structured AI feedback as a dictionary.
    """

    settings = get_settings()

    client = MoodleClient(
        base_url=settings.moodle_base_url,
        token=settings.moodle_token,
        rest_format=settings.moodle_rest_format,
    )

    assignment_context = build_student_assignment_context(
        client=client,
        student_user_id=student_user_id,
        course_id=course_id,
        assignment_id=assignment_id,
    )

    criterion_mapping = build_ai_criterion_mapping_from_moodle(
        client=client,
        course_module_id=assignment_context["course_module_id"],
        assignment_id=assignment_id,
        explicit_mappings=explicit_mappings,
    )

    student_competency_evidence = build_student_rubric_evidence(
        student_id=student_user_id,
        assignment_id=assignment_id,
        rubric_fillings=assignment_context.get("rubric", {}).get("rubric_fillings", []),
        criterion_mapping=criterion_mapping,
    )

    ai_input = build_assignment_ai_input(
        assignment_context=assignment_context,
        student_name=student_name,
        course_name=course_name,
        criterion_mapping=criterion_mapping,
    )

    ai_provider = get_ai_provider()

    feedback = ai_provider.generate_feedback(ai_input)

    return {
        "assignment_context": assignment_context,
        "criterion_mapping": criterion_mapping,
        "student_competency_evidence": student_rubric_evidence_to_dicts(
            student_competency_evidence
        ),
        "ai_input": ai_input,
        "ai_feedback": feedback.model_dump(),
    }
