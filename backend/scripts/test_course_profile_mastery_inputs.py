from mastery.mastery_model import calculate_mastery_report, mastery_report_to_dict
from moodle.normalisers.mastery_input_builder import (
    build_mastery_inputs_from_assignment_ai_input,
    build_mastery_inputs_from_quiz_contexts,
    merge_mastery_input_bundles,
)


def _assignment_ai_input() -> dict:
    return {
        "student": {
            "moodle_user_id": 9,
            "name": "Susan",
        },
        "course": {
            "course_id": 2,
            "course_name": "Introduction to IT",
        },
        "assessment": {
            "assignment_id": 1,
            "name": "Assignment 1",
        },
        "rubric_evidence": [
            {
                "criterion_id": 5,
                "criterion_title": "Explain IT concepts",
                "silo_id": "IT101-SILO1",
                "silo_description": "Explain foundational IT concepts.",
                "max_score": 10,
                "score_percent": 60,
            }
        ],
    }


def _quiz_contexts() -> list[dict]:
    return [
        {
            "is_valid_for_mastery": True,
            "student_user_id": 9,
            "course_id": 2,
            "quiz_id": 12,
            "quiz_name": "Quiz 1",
            "best_grade": {
                "grade_percent": 80,
                "grade": 8,
                "max_grade": 10,
            },
            "selected_attempt": {
                "attempt_id": 9001,
                "state": "finished",
            },
            "competency_mappings": [
                {
                    "competency_id": "101",
                    "competency_code": "IT101-SILO1",
                    "competency_name": "SILO 1",
                    "silo_id": "IT101-SILO1",
                    "silo_description": "Explain foundational IT concepts.",
                    "coverage_weight": 1.0,
                    "mapping_source": "moodle_activity_competency",
                }
            ],
        },
        {
            "is_valid_for_mastery": True,
            "student_user_id": 9,
            "course_id": 2,
            "quiz_id": 13,
            "quiz_name": "Quiz 2",
            "best_grade": {
                "grade_percent": 50,
                "grade": 5,
                "max_grade": 10,
            },
            "selected_attempt": {
                "attempt_id": 9002,
                "state": "submitted",
            },
            "competency_mappings": [
                {
                    "competency_id": "102",
                    "competency_code": "IT101-SILO2",
                    "competency_name": "SILO 2",
                    "silo_id": "IT101-SILO2",
                    "silo_description": "Apply IT concepts to workplace scenarios.",
                    "coverage_weight": 1.0,
                    "mapping_source": "moodle_activity_competency",
                }
            ],
        },
    ]


def test_combined_assignment_and_quiz_mastery_inputs() -> None:
    assignment_bundle = build_mastery_inputs_from_assignment_ai_input(
        ai_input=_assignment_ai_input(),
        assignment_weight_percent=50,
    )
    quiz_bundle = build_mastery_inputs_from_quiz_contexts(
        quiz_contexts=_quiz_contexts(),
        quiz_weight_percent_by_id={
            "12": 25,
            "13": 25,
        },
    )
    combined_bundle = merge_mastery_input_bundles(
        student_id="9",
        course_id="2",
        bundles=[assignment_bundle, quiz_bundle],
    )

    report = calculate_mastery_report(
        student_id=combined_bundle.student_id,
        course_id=combined_bundle.course_id,
        silos=combined_bundle.silos,
        assessments=combined_bundle.assessments,
        mappings=combined_bundle.mappings,
        results=combined_bundle.student_results,
    )
    report_dict = mastery_report_to_dict(report)

    assert len(combined_bundle.assessments) == 3
    assert len(combined_bundle.student_results) == 3
    assert report_dict["overall_mastery_score"] == 62.5

    silo_scores = {
        item["silo_id"]: item["mastery_score"]
        for item in report_dict["silo_mastery"]
    }

    assert silo_scores["IT101-SILO1"] == 66.67
    assert silo_scores["IT101-SILO2"] == 50


if __name__ == "__main__":
    test_combined_assignment_and_quiz_mastery_inputs()
    print("Course profile mastery input tests passed.")
