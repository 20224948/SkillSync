from dataclasses import asdict
import json
import logging

from moodle.evidence_mapper import (
    Competency,
    RubricCriterion,
    RubricLevel,
    build_ai_criterion_mapping,
    build_student_rubric_evidence,
    student_rubric_evidence_to_dicts,
)
from moodle.normalisers.ai_input_builder import build_assignment_ai_input
from moodle.normalisers.mastery_input_builder import (
    build_mastery_inputs_from_assignment_ai_input,
)
from mastery.mastery_model import calculate_mastery_report, mastery_report_to_dict


logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


COURSE_ID = "IT101"
ASSIGNMENT_ID = "assignment-1"
STUDENT_ID = "student-1"


def display_json(data: dict | list, title: str) -> None:
    """
    Prints JSON in a simple format that works without live Moodle access.
    """

    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2))


def build_mock_competencies() -> list[Competency]:
    """
    Simulates competencies returned by Moodle for Assignment 1.

    In live Moodle, these should come from:
    core_competency_list_course_module_competencies
    """

    return [
        Competency(
            id="comp-it101-silo1",
            code="IT101-SILO1",
            name="SILO 1 - Foundational IT Concepts",
            description="Explain foundational IT concepts.",
        ),
        Competency(
            id="comp-it101-silo2",
            code="IT101-SILO2",
            name="SILO 2 - IT in Organisations",
            description="Describe the role of IT in modern organisations.",
        ),
        Competency(
            id="comp-it101-silo3",
            code="IT101-SILO3",
            name="SILO 3 - Technical Communication",
            description=(
                "Communicate technical concepts clearly using appropriate "
                "structure and terminology."
            ),
        ),
        Competency(
            id="comp-it101-silo4",
            code="IT101-SILO4",
            name="SILO 4 - IT Problem Solving",
            description="Apply basic problem-solving to simple IT scenarios.",
        ),
    ]


def build_levels(starting_level_id: int) -> list[RubricLevel]:
    """
    Creates the IT101 rubric levels: 0, 10, 15, 20, 25.
    """

    scores = [0, 10, 15, 20, 25]

    return [
        RubricLevel(
            id=str(starting_level_id + index),
            score=score,
            definition=f"{score} points",
        )
        for index, score in enumerate(scores)
    ]


def build_mock_rubric_criteria() -> list[RubricCriterion]:
    """
    Simulates rubric criteria returned by Moodle's advanced grading definition.

    In live Moodle, these should come from core_grading_get_definitions.
    """

    return [
        RubricCriterion(
            id="5",
            assignment_id=ASSIGNMENT_ID,
            description="SILO 1 - Explanation of IT concepts",
            max_score=25,
            levels=build_levels(17),
        ),
        RubricCriterion(
            id="6",
            assignment_id=ASSIGNMENT_ID,
            description="SILO 2 - Role of IT in organisations",
            max_score=25,
            levels=build_levels(22),
        ),
        RubricCriterion(
            id="7",
            assignment_id=ASSIGNMENT_ID,
            description="SILO 3 - Technical communication",
            max_score=25,
            levels=build_levels(27),
        ),
        RubricCriterion(
            id="8",
            assignment_id=ASSIGNMENT_ID,
            description="SILO 4 - IT problem solving",
            max_score=25,
            levels=build_levels(32),
        ),
    ]


def build_mock_assignment_context() -> dict:
    """
    Simulates the normalised Moodle assignment context for one student.

    The selected level IDs below produce these scores:
    - SILO 1: 15 / 25 = 60%
    - SILO 2: 25 / 25 = 100%
    - SILO 3: 15 / 25 = 60%
    - SILO 4: 20 / 25 = 80%
    """

    return {
        "student_user_id": STUDENT_ID,
        "course_id": COURSE_ID,
        "assignment_id": ASSIGNMENT_ID,
        "course_module_id": "cmid-4",
        "assignment_name": "Assignment 1: Report",
        "assignment_max_grade": 100,
        "assignment_task": "Write a short report explaining introductory IT concepts.",
        "submission": {
            "submission_id": "submission-1",
            "attempt_number": 0,
            "status": "submitted",
            "latest": True,
            "submitted_files": [],
        },
        "grading": {
            "is_graded": True,
            "grading_status": "graded",
            "grade_id": "grade-1",
            "grade_percent": 75,
            "grade_display": "75 / 100",
        },
        "feedback": {
            "comment": (
                "Good organisation overall. Improve the explanation of core IT "
                "concepts and use more precise technical terminology."
            ),
            "feedback_files": [],
        },
        "rubric": {
            "rubric_fillings": [
                {
                    "criterion_id": "5",
                    "level_id": "19",
                    "remark": "Explanation is partly correct but needs more detail.",
                },
                {
                    "criterion_id": "6",
                    "level_id": "26",
                    "remark": "Strong discussion of IT in organisations.",
                },
                {
                    "criterion_id": "7",
                    "level_id": "29",
                    "remark": "Communication is understandable but terminology is uneven.",
                },
                {
                    "criterion_id": "8",
                    "level_id": "35",
                    "remark": "Good basic approach to solving the scenario.",
                },
            ],
        },
    }


def build_learning_support_ai_input(
    assignment_ai_input: dict,
    mastery_report: dict,
) -> dict:
    """
    Builds the final LLM payload from calculated mastery evidence.

    The important rule is that all scores are copied from the mastery engine.
    The LLM can explain and recommend, but it must not recalculate mastery.
    """

    return {
        "request_type": "generate_study_plan_feedback_mcqs_and_recommendations",
        "student": assignment_ai_input["student"],
        "course": assignment_ai_input["course"],
        "assessment": assignment_ai_input["assessment"],
        "mastery_result": mastery_report,
        "evidence_used": assignment_ai_input["rubric_evidence"],
        "teacher_feedback": assignment_ai_input["teacher_feedback"],
        "ai_guidance": {
            "instruction": (
                "Explain the calculated mastery result in student-friendly "
                "language, then generate a targeted study plan, MCQs, and "
                "recommendations linked to the weakest SILOs."
            ),
            "do_not_do": [
                "Do not invent or change mastery scores.",
                "Do not infer criterion-to-competency mappings.",
                "Only discuss strengths and weaknesses supported by evidence_used.",
            ],
        },
    }


def main() -> None:
    """
    Demonstrates the full IT101 evidence path without live Moodle access.
    """

    competencies = build_mock_competencies()
    rubric_criteria = build_mock_rubric_criteria()
    assignment_context = build_mock_assignment_context()

    # This simulates the future backend/database table. Only SILO 1 is mapped
    # explicitly here so the demo also proves the SILO-code fallback works for
    # SILO 2, SILO 3, and SILO 4.
    explicit_mappings = [
        {
            "assignment_id": ASSIGNMENT_ID,
            "criterion_id": "5",
            "competency_id": "comp-it101-silo1",
        }
    ]

    criterion_mapping = build_ai_criterion_mapping(
        assignment_id=ASSIGNMENT_ID,
        rubric_criteria=rubric_criteria,
        competencies=competencies,
        explicit_mappings=explicit_mappings,
    )

    student_evidence = build_student_rubric_evidence(
        student_id=STUDENT_ID,
        assignment_id=ASSIGNMENT_ID,
        rubric_fillings=assignment_context["rubric"]["rubric_fillings"],
        criterion_mapping=criterion_mapping,
    )

    assignment_ai_input = build_assignment_ai_input(
        assignment_context=assignment_context,
        student_name="Susan",
        course_name="Introduction to IT",
        criterion_mapping=criterion_mapping,
    )

    mastery_inputs = build_mastery_inputs_from_assignment_ai_input(
        ai_input=assignment_ai_input,
        assignment_weight_percent=100,
    )

    mastery_report = calculate_mastery_report(
        student_id=mastery_inputs.student_id,
        course_id=mastery_inputs.course_id,
        silos=mastery_inputs.silos,
        assessments=mastery_inputs.assessments,
        mappings=mastery_inputs.mappings,
        results=mastery_inputs.student_results,
    )

    mastery_report_dict = mastery_report_to_dict(mastery_report)

    learning_support_ai_input = build_learning_support_ai_input(
        assignment_ai_input=assignment_ai_input,
        mastery_report=mastery_report_dict,
    )

    display_json(
        {
            "competencies": [asdict(competency) for competency in competencies],
            "rubric_criteria": [asdict(criterion) for criterion in rubric_criteria],
        },
        "Simulated Moodle Competencies And Rubric Criteria",
    )

    display_json(
        criterion_mapping,
        "Resolved Criterion To Competency Mapping",
    )

    display_json(
        student_rubric_evidence_to_dicts(student_evidence),
        "Normalised Student Competency Evidence",
    )

    display_json(
        mastery_report_dict,
        "Calculated Mastery Report",
    )

    display_json(
        learning_support_ai_input,
        "Final Evidence-Based AI Input",
    )


if __name__ == "__main__":
    main()
