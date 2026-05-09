from dataclasses import dataclass

from mastery.mastery_model import (
    SILO,
    Assessment,
    AssessmentSiloMapping,
    StudentResult,
)


@dataclass(frozen=True)
class MockMasteryData:
    """
    Groups all mock mastery data together.

    This keeps the test file cleaner and makes it easier to replace
    mock data with real Moodle data later.
    """

    student_id: str
    student_name: str
    course_id: str
    course_name: str
    teacher_feedback: str

    silos: list[SILO]
    assessments: list[Assessment]
    mappings: list[AssessmentSiloMapping]
    student_results: list[StudentResult]


def get_mock_mastery_data() -> MockMasteryData:
    """
    Returns mock Moodle-style data for testing the Mastery Model.

    Later, this function can be replaced by data retrieved from Moodle.
    """

    silos = [
        SILO(
            silo_id="NET-SILO-1",
            course_id="NET101",
            title="Routing Concepts",
            description="Explain routing concepts, routing protocols, and how routers select paths.",
        ),
        SILO(
            silo_id="NET-SILO-2",
            course_id="NET101",
            title="IP Addressing and Subnetting",
            description="Apply IP addressing and subnetting concepts to calculate network ranges and host limits.",
        ),
        SILO(
            silo_id="NET-SILO-3",
            course_id="NET101",
            title="Network Security Controls",
            description="Apply basic network security controls such as ACLs to manage traffic flow.",
        ),
        SILO(
            silo_id="NET-SILO-4",
            course_id="NET101",
            title="Technical Explanation and Troubleshooting",
            description="Explain technical decisions clearly and troubleshoot basic network issues.",
        ),
    ]

    assessments = [
        Assessment(
            assessment_id="A1",
            course_id="NET101",
            name="Routing Fundamentals Quiz",
            weight_percent=10,
        ),
        Assessment(
            assessment_id="A2",
            course_id="NET101",
            name="Subnetting Quiz",
            weight_percent=10,
        ),
        Assessment(
            assessment_id="A3",
            course_id="NET101",
            name="Network Design Assignment",
            weight_percent=30,
        ),
        Assessment(
            assessment_id="A4",
            course_id="NET101",
            name="ACL and OSPF Lab Practical",
            weight_percent=20,
        ),
    ]

    mappings = [
        # Routing quiz mostly tests routing concepts.
        AssessmentSiloMapping("A1", "NET-SILO-1", 0.8),
        AssessmentSiloMapping("A1", "NET-SILO-4", 0.2),

        # Subnetting quiz only tests subnetting.
        AssessmentSiloMapping("A2", "NET-SILO-2", 1.0),

        # Network design assignment tests multiple learning outcomes.
        AssessmentSiloMapping("A3", "NET-SILO-1", 0.3),
        AssessmentSiloMapping("A3", "NET-SILO-2", 0.2),
        AssessmentSiloMapping("A3", "NET-SILO-3", 0.3),
        AssessmentSiloMapping("A3", "NET-SILO-4", 0.2),

        # Lab practical focuses on routing and ACL configuration.
        AssessmentSiloMapping("A4", "NET-SILO-1", 0.4),
        AssessmentSiloMapping("A4", "NET-SILO-3", 0.4),
        AssessmentSiloMapping("A4", "NET-SILO-4", 0.2),
    ]

    student_results = [
        StudentResult(
            student_id="s1001",
            assessment_id="A1",
            score_percent=55,
        ),
        StudentResult(
            student_id="s1001",
            assessment_id="A2",
            score_percent=48,
        ),
        StudentResult(
            student_id="s1001",
            assessment_id="A3",
            score_percent=62,
        ),
        StudentResult(
            student_id="s1001",
            assessment_id="A4",
            score_percent=58,
        ),
    ]

    return MockMasteryData(
        student_id="s1001",
        student_name="Alex",
        course_id="NET101",
        course_name="Networking Fundamentals",
        teacher_feedback="Needs stronger explanation of routing concepts and more subnetting practice.",
        silos=silos,
        assessments=assessments,
        mappings=mappings,
        student_results=student_results,
    )