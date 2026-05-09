from dataclasses import dataclass, asdict
from typing import Literal


ConfidenceLevel = Literal["none", "low", "medium", "high"]


@dataclass(frozen=True)
class SILO:
    """
    Represents a Subject Intended Learning Outcome.
    """

    silo_id: str
    course_id: str
    title: str
    description: str


@dataclass(frozen=True)
class Assessment:
    """
    Represents an assessment task in a subject.
    """

    assessment_id: str
    course_id: str
    name: str

    # The percentage this assessment contributes to the overall subject grade.
    weight_percent: float


@dataclass(frozen=True)
class AssessmentSiloMapping:
    """
    Links an assessment to one or more SILOs.

    coverage_weight represents how much of the assessment tests this SILO.
    Example:
    - 1.0 means the whole assessment tests this SILO.
    - 0.5 means half of the assessment tests this SILO.
    """

    assessment_id: str
    silo_id: str
    coverage_weight: float


@dataclass(frozen=True)
class StudentResult:
    """
    Represents a student's result for one assessment.
    """

    student_id: str
    assessment_id: str

    # Student score as a percentage, e.g. 75 means 75%.
    score_percent: float


@dataclass
class SiloEvidence:
    """
    Stores the assessment evidence used to calculate a SILO mastery score.
    """

    assessment_id: str
    assessment_name: str
    score_percent: float
    assessment_weight_percent: float
    coverage_weight: float
    evidence_weight: float


@dataclass
class SiloMastery:
    """
    Represents the calculated mastery score for one SILO.
    """

    silo_id: str
    title: str
    description: str

    # None means there was no assessment evidence for this SILO yet.
    mastery_score: float | None

    confidence: ConfidenceLevel
    evidence_count: int
    total_evidence_weight: float
    evidence: list[SiloEvidence]


@dataclass
class MasteryReport:
    """
    Final mastery report for a student in one course.
    """

    student_id: str
    course_id: str
    overall_mastery_score: float | None
    silo_mastery: list[SiloMastery]
    weakest_silos: list[SiloMastery]


def _clamp_score(score: float) -> float:
    """
    Keeps a score between 0 and 100.
    """

    return max(0, min(100, score))


def _calculate_confidence(evidence_count: int, total_evidence_weight: float) -> ConfidenceLevel:
    """
    Estimates how reliable a SILO mastery score is.

    More assessments and more total assessment weight means higher confidence.
    """

    if evidence_count == 0:
        return "none"

    if evidence_count >= 3 and total_evidence_weight >= 30:
        return "high"

    if evidence_count >= 2 or total_evidence_weight >= 15:
        return "medium"

    return "low"


def calculate_mastery_report(
    student_id: str,
    course_id: str,
    silos: list[SILO],
    assessments: list[Assessment],
    mappings: list[AssessmentSiloMapping],
    results: list[StudentResult],
    weak_threshold: float = 70,
) -> MasteryReport:
    """
    Calculates per-SILO mastery and overall subject mastery for one student.

    Formula:
    SILO mastery =
    sum(student_score * assessment_weight * SILO_coverage)
    /
    sum(assessment_weight * SILO_coverage)
    """

    # Store assessments by ID for fast lookup.
    assessment_lookup = {
        assessment.assessment_id: assessment
        for assessment in assessments
        if assessment.course_id == course_id
    }

    # Only use results for the selected student.
    student_results = [
        result for result in results
        if result.student_id == student_id
    ]

    silo_mastery_results: list[SiloMastery] = []

    for silo in silos:
        if silo.course_id != course_id:
            continue

        weighted_score_total = 0.0
        evidence_weight_total = 0.0
        evidence_items: list[SiloEvidence] = []

        for result in student_results:
            assessment = assessment_lookup.get(result.assessment_id)

            # Skip results for assessments that are not part of this course.
            if assessment is None:
                continue

            # Find mappings where this assessment tests the current SILO.
            matching_mappings = [
                mapping for mapping in mappings
                if mapping.assessment_id == assessment.assessment_id
                and mapping.silo_id == silo.silo_id
            ]

            for mapping in matching_mappings:
                # This is how strongly this assessment result contributes to the SILO.
                evidence_weight = assessment.weight_percent * mapping.coverage_weight

                # Add weighted score contribution.
                weighted_score_total += _clamp_score(result.score_percent) * evidence_weight
                evidence_weight_total += evidence_weight

                evidence_items.append(
                    SiloEvidence(
                        assessment_id=assessment.assessment_id,
                        assessment_name=assessment.name,
                        score_percent=_clamp_score(result.score_percent),
                        assessment_weight_percent=assessment.weight_percent,
                        coverage_weight=mapping.coverage_weight,
                        evidence_weight=round(evidence_weight, 2),
                    )
                )

        if evidence_weight_total == 0:
            mastery_score = None
        else:
            mastery_score = round(weighted_score_total / evidence_weight_total, 2)

        confidence = _calculate_confidence(
            evidence_count=len(evidence_items),
            total_evidence_weight=evidence_weight_total,
        )

        silo_mastery_results.append(
            SiloMastery(
                silo_id=silo.silo_id,
                title=silo.title,
                description=silo.description,
                mastery_score=mastery_score,
                confidence=confidence,
                evidence_count=len(evidence_items),
                total_evidence_weight=round(evidence_weight_total, 2),
                evidence=evidence_items,
            )
        )

    # Only include SILOs that have at least one evidence item.
    silos_with_scores = [
        silo for silo in silo_mastery_results
        if silo.mastery_score is not None and silo.total_evidence_weight > 0
    ]

    if not silos_with_scores:
        overall_mastery_score = None
    else:
        # Overall mastery is weighted by how much evidence exists for each SILO.
        overall_weighted_total = sum(
            silo.mastery_score * silo.total_evidence_weight
            for silo in silos_with_scores
        )

        overall_weight_total = sum(
            silo.total_evidence_weight
            for silo in silos_with_scores
        )

        overall_mastery_score = round(overall_weighted_total / overall_weight_total, 2)

    # Weakest SILOs are the lowest scoring SILOs under the threshold.
    weakest_silos = sorted(
        [
            silo for silo in silos_with_scores
            if silo.mastery_score < weak_threshold
        ],
        key=lambda silo: silo.mastery_score
    )

    return MasteryReport(
        student_id=student_id,
        course_id=course_id,
        overall_mastery_score=overall_mastery_score,
        silo_mastery=silo_mastery_results,
        weakest_silos=weakest_silos[:3],
    )


def mastery_report_to_dict(report: MasteryReport) -> dict:
    """
    Converts the mastery report into a dictionary so it can be printed,
    passed to the AI model, or stored as JSON later.
    """

    return asdict(report)