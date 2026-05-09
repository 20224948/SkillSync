from moodle.client import MoodleClient


def get_grading_definitions(
    client: MoodleClient,
    course_module_id: int,
    area_name: str = "submissions",
    active_only: int = 1,
) -> dict:
    """
    Gets the advanced grading definitions for a Moodle activity.

    For assignments, the area_name is usually "submissions".

    course_module_id is the cmid, not the assignment id.
    Example:
    - Assignment ID / assignid = 1
    - Course module ID / cmid = 4
    """

    return client.call(
        "core_grading_get_definitions",
        {
            "cmids[0]": course_module_id,
            "areaname": area_name,
            "activeonly": active_only,
        },
    )


def get_gradingform_instances(
    client: MoodleClient,
    definition_id: int,
) -> dict:
    """
    Gets grading form instances/fillings for a grading definition.

    This may include completed rubric data, depending on Moodle's response
    structure and the grading method used.
    """

    return client.call(
        "core_grading_get_gradingform_instances",
        {
            "definitionid": definition_id,
        },
    )


def extract_definition_ids(definitions_response: dict) -> list[int]:
    """
    Extracts grading definition IDs from the Moodle response.
    """

    definition_ids: list[int] = []

    for area in definitions_response.get("areas", []):
        for definition in area.get("definitions", []):
            definition_id = definition.get("id")

            if definition_id is not None:
                definition_ids.append(int(definition_id))

    return definition_ids


def summarise_grading_definitions(definitions_response: dict) -> list[dict]:
    """
    Creates a smaller summary of the grading definition response.

    The raw Moodle response can be large, so this summary helps identify:
    - cmid
    - active grading method
    - definition id
    - rubric criteria
    """

    summaries: list[dict] = []

    for area in definitions_response.get("areas", []):
        area_summary = {
            "course_module_id": area.get("cmid"),
            "context_id": area.get("contextid"),
            "component": area.get("component"),
            "area_name": area.get("areaname"),
            "active_method": area.get("activemethod"),
            "definitions": [],
        }

        for definition in area.get("definitions", []):
            definition_summary = {
                "definition_id": definition.get("id"),
                "name": definition.get("name"),
                "description": definition.get("description"),
                "method": definition.get("method"),
                "status": definition.get("status"),
                "rubric_criteria": [],
            }

            # Rubric data is usually inside definition["rubric"]["criteria"],
            # but some Moodle responses use "rubric_criteria" for definitions.
            rubric = definition.get("rubric", {})
            criteria = rubric.get("criteria") or rubric.get("rubric_criteria") or []

            for criterion in criteria:
                criterion_summary = {
                    "criterion_id": criterion.get("id"),
                    "description": criterion.get("description"),
                    "sort_order": criterion.get("sortorder"),
                    "levels": [],
                }

                for level in criterion.get("levels", []):
                    criterion_summary["levels"].append(
                        {
                            "level_id": level.get("id"),
                            "definition": level.get("definition"),
                            "score": level.get("score"),
                        }
                    )

                definition_summary["rubric_criteria"].append(criterion_summary)

            area_summary["definitions"].append(definition_summary)

        summaries.append(area_summary)

    return summaries


def summarise_grading_instances(instances_response: dict) -> list[dict]:
    """
    Creates a smaller summary of grading form instances/fillings.

    This helps inspect whether Moodle returns completed rubric selections,
    selected levels, remarks, and raw grades in structured form.
    """

    summaries: list[dict] = []

    for instance in instances_response.get("instances", []):
        instance_summary = {
            "instance_id": instance.get("id"),
            "definition_id": instance.get("definitionid"),
            "rater_id": instance.get("raterid"),
            "item_id": instance.get("itemid"),
            "raw_grade": instance.get("rawgrade"),
            "status": instance.get("status"),
            "timemodified": instance.get("timemodified"),
            "rubric_fillings": [],
        }

        # Depending on Moodle version, fillings may appear in different shapes.
        # This handles the common rubric structure if it is returned.
        rubric = instance.get("rubric", {})
        criteria = rubric.get("criteria", [])

        for criterion in criteria:
            instance_summary["rubric_fillings"].append(
                {
                    "criterion_id": criterion.get("criterionid")
                    or criterion.get("id"),
                    "level_id": criterion.get("levelid"),
                    "remark": criterion.get("remark"),
                    "remark_format": criterion.get("remarkformat"),
                }
            )

        summaries.append(instance_summary)

    return summaries

def find_rubric_instance_for_grade(
    instances_response: dict,
    grade_id: int,
) -> dict | None:
    """
    Finds the completed rubric instance linked to a student's grade.

    Moodle links grading form instances to grade records using itemid.
    For assignment rubrics, itemid usually matches the assignment grade id.
    """

    for instance in instances_response.get("instances", []):
        item_id = instance.get("itemid")

        if item_id is not None and int(item_id) == int(grade_id):
            return instance

    return None
