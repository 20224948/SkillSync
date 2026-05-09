from __future__ import annotations

from dataclasses import asdict, dataclass
import html
import logging
import re
from typing import Any

from moodle.client import MoodleClient
from moodle.services.competencies import get_course_module_competencies
from moodle.services.rubrics import get_grading_definitions


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Competency:
    """
    Clean internal representation of a Moodle competency/SILO.

    id is the stable Moodle competency ID. code is the human/project code such as
    IT101-SILO1, usually stored in Moodle as idnumber or shortname.
    """

    id: str
    code: str
    name: str
    description: str = ""


@dataclass(frozen=True)
class RubricLevel:
    """
    One selectable level inside a Moodle rubric criterion.
    """

    id: str
    score: float
    definition: str = ""


@dataclass(frozen=True)
class RubricCriterion:
    """
    Clean internal representation of one Moodle rubric criterion.
    """

    id: str
    assignment_id: str
    description: str
    max_score: float
    levels: list[RubricLevel]


@dataclass(frozen=True)
class RubricCriterionToCompetencyMapping:
    """
    Project-level link from a rubric criterion to the competency it measures.

    mapping_source is useful for audits:
    - explicit means a database/config mapping chose the competency.
    - silo_code_fallback means the development fallback matched a SILO code.
    """

    assignment_id: str
    criterion_id: str
    competency_id: str
    mapping_source: str


@dataclass(frozen=True)
class StudentRubricEvidence:
    """
    One student's rubric score converted into competency evidence.
    """

    student_id: str
    assignment_id: str
    criterion_id: str
    competency_id: str
    score: float
    max_score: float
    normalised_score: float
    feedback: str = ""
    mapping_source: str = ""


def _clean_text(value: object) -> str:
    """
    Converts Moodle HTML-ish values into simple text for matching and AI input.
    """

    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def _normalise_id(value: object) -> str:
    """
    Keeps Moodle IDs consistent when some API responses return ints and others
    return strings.
    """

    return str(value).strip()


def _safe_float(value: object, default: float = 0.0) -> float:
    """
    Converts Moodle numeric values into floats.
    """

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_silo_numbers(*values: object) -> set[str]:
    """
    Finds SILO numbers in strings such as:
    - SILO 1
    - SILO1
    - IT101-SILO1
    - IT101-SILO-1

    This is only a development fallback. Explicit criterion_id -> competency_id
    mappings are still the best source of truth.
    """

    silo_numbers: set[str] = set()

    for value in values:
        text = _clean_text(value).upper()

        for match in re.finditer(r"\bSILO\s*-?\s*(\d+)\b", text):
            silo_numbers.add(str(int(match.group(1))))

    return silo_numbers


def _walk_dicts(value: Any) -> list[dict]:
    """
    Recursively returns dictionaries from a Moodle response.

    Moodle competency responses differ slightly between endpoints and versions,
    so the normaliser below looks for likely competency objects without assuming
    one exact response shape.
    """

    dicts: list[dict] = []

    if isinstance(value, dict):
        dicts.append(value)

        for child in value.values():
            dicts.extend(_walk_dicts(child))

    elif isinstance(value, list):
        for child in value:
            dicts.extend(_walk_dicts(child))

    return dicts


def normalise_competencies_from_moodle_response(response: dict | list) -> list[Competency]:
    """
    Extracts Moodle competencies from course or course-module competency output.

    Moodle often wraps the competency inside a "competency" field. This function
    accepts both wrapped and direct competency dictionaries.
    """

    competencies: dict[str, Competency] = {}

    for item in _walk_dicts(response):
        candidate = item.get("competency") if isinstance(item.get("competency"), dict) else item

        competency_id = candidate.get("id")
        has_competency_shape = (
            competency_id is not None
            and (
                candidate.get("idnumber") is not None
                or candidate.get("shortname") is not None
                or candidate.get("description") is not None
            )
        )

        if not has_competency_shape:
            continue

        competency_id = _normalise_id(competency_id)
        code = _clean_text(candidate.get("idnumber") or candidate.get("shortname") or competency_id)
        name = _clean_text(candidate.get("shortname") or candidate.get("idnumber") or code)
        description = _clean_text(candidate.get("description"))

        competencies[competency_id] = Competency(
            id=competency_id,
            code=code,
            name=name,
            description=description,
        )

    return list(competencies.values())


def normalise_rubric_criteria_from_grading_definitions(
    definitions_response: dict,
    assignment_id: int | str,
) -> list[RubricCriterion]:
    """
    Extracts clean rubric criteria and level scores from core_grading_get_definitions.
    """

    rubric_criteria: list[RubricCriterion] = []

    for area in definitions_response.get("areas", []):
        for definition in area.get("definitions", []):
            rubric = definition.get("rubric", {})

            # Moodle versions/plugins can return rubric definition criteria
            # using either "criteria" or "rubric_criteria". Your current
            # Moodle test site uses "rubric_criteria", while grading form
            # instances use "criteria".
            criteria = rubric.get("criteria") or rubric.get("rubric_criteria") or []

            for criterion in criteria:
                criterion_id = criterion.get("id") or criterion.get("criterionid")

                if criterion_id is None:
                    logger.warning(
                        "Skipping a Moodle rubric criterion because it has no criterion ID."
                    )
                    continue

                levels = [
                    RubricLevel(
                        id=_normalise_id(level.get("id")),
                        score=_safe_float(level.get("score")),
                        definition=_clean_text(level.get("definition")),
                    )
                    for level in criterion.get("levels", [])
                    if level.get("id") is not None
                ]

                max_score = max((level.score for level in levels), default=0.0)

                rubric_criteria.append(
                    RubricCriterion(
                        id=_normalise_id(criterion_id),
                        assignment_id=_normalise_id(assignment_id),
                        description=_clean_text(criterion.get("description")),
                        max_score=max_score,
                        levels=levels,
                    )
                )

    return rubric_criteria


def _normalise_explicit_mappings(
    explicit_mappings: dict | list | None,
    assignment_id: str,
) -> dict[str, str]:
    """
    Accepts simple explicit mapping formats and returns criterion_id -> competency_id.

    Supported examples:
    {"5": "123"}
    {"5": {"competency_id": "123"}}
    [{"assignment_id": "1", "criterion_id": "5", "competency_id": "123"}]
    {"mappings": [{"criterion_id": "5", "competency_id": "123"}]}
    """

    if explicit_mappings is None:
        return {}

    if isinstance(explicit_mappings, dict) and isinstance(explicit_mappings.get("mappings"), list):
        explicit_mappings = explicit_mappings["mappings"]

    mappings: dict[str, str] = {}

    if isinstance(explicit_mappings, dict):
        for criterion_id, value in explicit_mappings.items():
            if isinstance(value, dict):
                competency_id = value.get("competency_id")
                mapping_assignment_id = value.get("assignment_id")
            else:
                competency_id = value
                mapping_assignment_id = None

            if mapping_assignment_id is not None and _normalise_id(mapping_assignment_id) != assignment_id:
                continue

            if competency_id is not None:
                mappings[_normalise_id(criterion_id)] = _normalise_id(competency_id)

    elif isinstance(explicit_mappings, list):
        for item in explicit_mappings:
            if isinstance(item, RubricCriterionToCompetencyMapping):
                criterion_id = item.criterion_id
                competency_id = item.competency_id
                mapping_assignment_id = item.assignment_id
            elif isinstance(item, dict):
                criterion_id = item.get("criterion_id")
                competency_id = item.get("competency_id")
                mapping_assignment_id = item.get("assignment_id")
            else:
                continue

            if criterion_id is None or competency_id is None:
                continue

            if mapping_assignment_id is not None and _normalise_id(mapping_assignment_id) != assignment_id:
                continue

            mappings[_normalise_id(criterion_id)] = _normalise_id(competency_id)

    return mappings


def resolve_rubric_competency_mappings(
    assignment_id: int | str,
    rubric_criteria: list[RubricCriterion],
    competencies: list[Competency],
    explicit_mappings: dict | list | None = None,
) -> list[RubricCriterionToCompetencyMapping]:
    """
    Resolves rubric criterion -> competency links.

    Priority:
    1. Explicit criterion_id -> competency_id mappings from config/database.
    2. Development fallback that matches SILO codes in criterion/competency text.
    3. Warning and skip if no safe mapping can be found.
    """

    assignment_id_text = _normalise_id(assignment_id)
    competencies_by_id = {competency.id: competency for competency in competencies}
    explicit_by_criterion = _normalise_explicit_mappings(
        explicit_mappings=explicit_mappings,
        assignment_id=assignment_id_text,
    )

    resolved_mappings: list[RubricCriterionToCompetencyMapping] = []

    for criterion in rubric_criteria:
        criterion_id = _normalise_id(criterion.id)
        explicit_competency_id = explicit_by_criterion.get(criterion_id)

        if explicit_competency_id:
            if explicit_competency_id in competencies_by_id:
                resolved_mappings.append(
                    RubricCriterionToCompetencyMapping(
                        assignment_id=assignment_id_text,
                        criterion_id=criterion_id,
                        competency_id=explicit_competency_id,
                        mapping_source="explicit",
                    )
                )
                continue

            logger.warning(
                "Explicit rubric mapping ignored: criterion_id=%s points to "
                "competency_id=%s, but that competency is not linked to assignment_id=%s.",
                criterion_id,
                explicit_competency_id,
                assignment_id_text,
            )

        criterion_silos = _extract_silo_numbers(criterion.description)

        if not criterion_silos:
            logger.warning(
                "Could not map rubric criterion_id=%s because its description "
                "does not contain a SILO code.",
                criterion_id,
            )
            continue

        matching_competencies = [
            competency for competency in competencies
            if criterion_silos.intersection(
                _extract_silo_numbers(
                    competency.code,
                    competency.name,
                    competency.description,
                )
            )
        ]

        if len(matching_competencies) == 1:
            resolved_mappings.append(
                RubricCriterionToCompetencyMapping(
                    assignment_id=assignment_id_text,
                    criterion_id=criterion_id,
                    competency_id=matching_competencies[0].id,
                    mapping_source="silo_code_fallback",
                )
            )
            continue

        if not matching_competencies:
            logger.warning(
                "Could not map rubric criterion_id=%s to a competency. "
                "Add an explicit criterion_id -> competency_id mapping.",
                criterion_id,
            )
            continue

        logger.warning(
            "Could not map rubric criterion_id=%s because SILO fallback was "
            "ambiguous. Candidate competency_ids=%s. Add an explicit mapping.",
            criterion_id,
            [competency.id for competency in matching_competencies],
        )

    return resolved_mappings


def build_ai_criterion_mapping(
    assignment_id: int | str,
    rubric_criteria: list[RubricCriterion],
    competencies: list[Competency],
    explicit_mappings: dict | list | None = None,
) -> dict[str, dict]:
    """
    Builds the enrichment dictionary consumed by build_assignment_ai_input().

    The existing AI input builder already expects a criterion mapping. This
    function keeps that interface, but replaces the temporary hardcoded data
    with Moodle-backed rubric and competency data.
    """

    mappings = resolve_rubric_competency_mappings(
        assignment_id=assignment_id,
        rubric_criteria=rubric_criteria,
        competencies=competencies,
        explicit_mappings=explicit_mappings,
    )

    criteria_by_id = {criterion.id: criterion for criterion in rubric_criteria}
    competencies_by_id = {competency.id: competency for competency in competencies}

    ai_mapping: dict[str, dict] = {}

    for mapping in mappings:
        criterion = criteria_by_id.get(mapping.criterion_id)
        competency = competencies_by_id.get(mapping.competency_id)

        if criterion is None or competency is None:
            continue

        ai_mapping[mapping.criterion_id] = {
            "criterion_id": mapping.criterion_id,
            "competency_id": competency.id,
            "competency_code": competency.code,
            "competency_name": competency.name,
            "mapping_source": mapping.mapping_source,
            # Keep the older field names so existing mastery conversion keeps
            # working while the project moves from SILO-only language to
            # Moodle competency IDs.
            "silo_id": competency.code or competency.id,
            "title": criterion.description or competency.name,
            "silo_description": competency.description or competency.name,
            "max_score": criterion.max_score,
            "levels": {
                level.id: level.score
                for level in criterion.levels
            },
        }

    return ai_mapping


def build_ai_criterion_mapping_from_moodle(
    client: MoodleClient,
    course_module_id: int,
    assignment_id: int | str,
    explicit_mappings: dict | list | None = None,
) -> dict[str, dict]:
    """
    Fetches Moodle rubric/competency data and builds the AI criterion mapping.

    This uses activity-level competency links, not only course-level
    competencies, because the assignment decides which competencies are relevant
    to the rubric evidence.
    """

    definitions_response = get_grading_definitions(
        client=client,
        course_module_id=course_module_id,
        area_name="submissions",
        active_only=1,
    )

    rubric_criteria = normalise_rubric_criteria_from_grading_definitions(
        definitions_response=definitions_response,
        assignment_id=assignment_id,
    )

    competencies_response = get_course_module_competencies(
        client=client,
        course_module_id=course_module_id,
    )

    competencies = normalise_competencies_from_moodle_response(competencies_response)

    if not competencies:
        logger.warning(
            "No competencies were returned for course_module_id=%s. "
            "Check that the Moodle assignment activity has competencies linked.",
            course_module_id,
        )

    if not rubric_criteria:
        logger.warning(
            "No rubric criteria were returned for course_module_id=%s. "
            "Check that the assignment uses Moodle rubric advanced grading.",
            course_module_id,
        )

    return build_ai_criterion_mapping(
        assignment_id=assignment_id,
        rubric_criteria=rubric_criteria,
        competencies=competencies,
        explicit_mappings=explicit_mappings,
    )


def _lookup_level_score(levels: dict, level_id: object) -> float | None:
    """
    Finds a selected level score even if Moodle returns IDs as ints in one place
    and strings in another.
    """

    if level_id in levels:
        return _safe_float(levels[level_id])

    level_id_text = _normalise_id(level_id)

    if level_id_text in levels:
        return _safe_float(levels[level_id_text])

    for key, value in levels.items():
        if _normalise_id(key) == level_id_text:
            return _safe_float(value)

    return None


def build_student_rubric_evidence(
    student_id: int | str,
    assignment_id: int | str,
    rubric_fillings: list[dict],
    criterion_mapping: dict[str, dict],
) -> list[StudentRubricEvidence]:
    """
    Converts selected rubric levels into competency evidence for one student.

    This is the normalised evidence layer between Moodle and the mastery engine.
    The mastery score is still calculated later by mastery.mastery_model.
    """

    evidence_items: list[StudentRubricEvidence] = []

    for filling in rubric_fillings:
        criterion_id = _normalise_id(filling.get("criterion_id"))
        mapping = criterion_mapping.get(criterion_id)

        if mapping is None:
            logger.warning(
                "Skipping rubric filling for criterion_id=%s because no "
                "competency mapping was resolved.",
                criterion_id,
            )
            continue

        selected_score = _lookup_level_score(
            levels=mapping.get("levels", {}),
            level_id=filling.get("level_id"),
        )
        max_score = _safe_float(mapping.get("max_score"))

        if selected_score is None or max_score <= 0:
            logger.warning(
                "Skipping rubric filling for criterion_id=%s because the "
                "selected level score or max score is missing.",
                criterion_id,
            )
            continue

        evidence_items.append(
            StudentRubricEvidence(
                student_id=_normalise_id(student_id),
                assignment_id=_normalise_id(assignment_id),
                criterion_id=criterion_id,
                competency_id=_normalise_id(mapping.get("competency_id")),
                score=selected_score,
                max_score=max_score,
                normalised_score=round((selected_score / max_score) * 100, 2),
                feedback=_clean_text(filling.get("remark")),
                mapping_source=_clean_text(mapping.get("mapping_source")),
            )
        )

    return evidence_items


def student_rubric_evidence_to_dicts(
    evidence_items: list[StudentRubricEvidence],
) -> list[dict]:
    """
    Converts evidence dataclasses to dictionaries for JSON output or storage.
    """

    return [asdict(item) for item in evidence_items]
