from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from api.main import (
    _enrich_courses_with_profiles,
    _normalise_enrolled_course,
    _require_enrolled_course,
)


def test_course_normalisation() -> None:
    course = _normalise_enrolled_course(
        {
            "id": "12",
            "shortname": "IT102",
            "fullname": "Introduction to Networking",
            "displayname": "Networking Fundamentals",
            "visible": "0",
        }
    )

    assert course == {
        "course_id": 12,
        "shortname": "IT102",
        "fullname": "Introduction to Networking",
        "display_name": "Networking Fundamentals",
        "visible": False,
    }


def test_course_profile_enrichment() -> None:
    now = datetime.now(UTC)
    courses = [
        {
            "course_id": 12,
            "shortname": "IT102",
            "fullname": "Introduction to Networking",
            "display_name": "Introduction to Networking",
            "visible": True,
        },
        {
            "course_id": 13,
            "shortname": "IT103",
            "fullname": "Databases",
            "display_name": "Databases",
            "visible": True,
        },
        {
            "course_id": 14,
            "shortname": "IT104",
            "fullname": "Programming",
            "display_name": "Programming",
            "visible": True,
        },
    ]
    summaries = [
        {
            "id": "fresh-report-id",
            "report_key": "moodle:course:12:student:9",
            "course_moodle_id": "12",
            "overall_mastery_score": 74.5,
            "generated_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
        {
            "id": "stale-report-id",
            "report_key": "moodle:course:14:student:9",
            "course_moodle_id": "14",
            "overall_mastery_score": 61,
            "generated_at": (now - timedelta(hours=2)).isoformat(),
            "updated_at": (now - timedelta(hours=2)).isoformat(),
        },
    ]

    enriched = _enrich_courses_with_profiles(
        enrolled_courses=courses,
        profile_summaries=summaries,
        freshness_minutes=60,
    )

    profiles_by_course = {
        course["course_id"]: course["profile"]
        for course in enriched
    }

    assert profiles_by_course[12]["status"] == "ready"
    assert profiles_by_course[12]["learning_report_id"] == "fresh-report-id"
    assert profiles_by_course[12]["is_stale"] is False
    assert profiles_by_course[13]["status"] == "not_generated"
    assert profiles_by_course[13]["is_stale"] is None
    assert profiles_by_course[14]["status"] == "ready"
    assert profiles_by_course[14]["is_stale"] is True


def test_enrolment_guard() -> None:
    enrolled_courses = [
        {
            "course_id": 12,
            "shortname": "IT102",
            "fullname": "Introduction to Networking",
            "display_name": "Introduction to Networking",
            "visible": True,
        }
    ]

    assert _require_enrolled_course(enrolled_courses, 12)["course_id"] == 12

    try:
        _require_enrolled_course(enrolled_courses, 99)
    except HTTPException as error:
        assert error.status_code == 404
        assert error.detail == "Course was not found for this student."
    else:
        raise AssertionError("Expected non-enrolled course to raise HTTPException.")


if __name__ == "__main__":
    test_course_normalisation()
    test_course_profile_enrichment()
    test_enrolment_guard()
    print("API course access tests passed.")
