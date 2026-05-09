from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.auth import AuthenticatedUser, get_authenticated_user
from config import get_settings
from moodle.client import MoodleClient
from moodle.services.users import get_user_by_field, get_user_courses
from repositories.supabase_learning_reports import SupabaseLearningReportRepository
from services.report_orchestration_service import (
    get_or_generate_student_learning_profile,
    get_report_generation_status,
)


logger = logging.getLogger("skillsync.api")


class ProfileRefreshRequest(BaseModel):
    course_id: int = Field(description="Moodle course ID.")
    course_name: str | None = Field(default=None, description="Optional course name.")
    assignment_ids: list[int] | None = Field(
        default=None,
        description="Optional Moodle assignment IDs to include.",
    )
    quiz_ids: list[int] | None = Field(
        default=None,
        description="Optional Moodle quiz IDs to include.",
    )
    assessment_weights: dict[str, Any] | None = Field(
        default=None,
        description="Optional assignment/quiz weighting config.",
    )
    explicit_assignment_mappings: dict | list | None = Field(
        default=None,
        description="Optional assignment rubric criterion to competency mappings.",
    )
    explicit_quiz_mappings: dict | list | None = Field(
        default=None,
        description="Optional quiz to competency mappings.",
    )


def _build_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SkillSync Backend API",
        version="1.0.0",
        description="Thin API around the SkillSync Moodle, mastery, AI, and Supabase pipeline.",
    )

    origins = [
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
    ] or ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    return app


app = _build_app()


def _log_event(event: str, **fields: Any) -> None:
    logger.info(
        json.dumps(
            {
                "event": event,
                **fields,
            },
            default=str,
            sort_keys=True,
        )
    )


def _safe_int(value: object, field_name: str) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student record has an invalid {field_name}.",
        ) from error


def _moodle_display_name(user: dict) -> str | None:
    return (
        user.get("fullname")
        or " ".join(
            part
            for part in [user.get("firstname"), user.get("lastname")]
            if part
        )
        or user.get("username")
    )


def _build_moodle_client() -> MoodleClient:
    settings = get_settings()

    try:
        return MoodleClient(
            base_url=settings.moodle_base_url,
            token=settings.moodle_token,
            rest_format=settings.moodle_rest_format,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _is_profile_stale(profile: dict, freshness_minutes: int) -> bool:
    generated_at = _parse_timestamp(profile.get("generated_at"))

    if generated_at is None:
        return True

    oldest_allowed = datetime.now(UTC) - timedelta(minutes=freshness_minutes)

    return generated_at < oldest_allowed


def _normalise_course_visibility(value: object) -> bool:
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no"}

    return bool(value)


def _normalise_enrolled_course(course: dict) -> dict:
    try:
        course_id = int(str(course.get("id")))
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Moodle returned an invalid course enrolment.",
        ) from error

    display_name = (
        course.get("displayname")
        or course.get("fullname")
        or course.get("shortname")
        or str(course_id)
    )

    return {
        "course_id": course_id,
        "shortname": course.get("shortname"),
        "fullname": course.get("fullname"),
        "display_name": display_name,
        "visible": _normalise_course_visibility(course.get("visible")),
    }


def _get_enrolled_courses(moodle_user_id: int) -> list[dict]:
    client = _build_moodle_client()

    try:
        courses = get_user_courses(
            client=client,
            user_id=moodle_user_id,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch Moodle course enrolments.",
        ) from error

    if not isinstance(courses, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Moodle returned an invalid course enrolment response.",
        )

    enrolled_courses = [
        _normalise_enrolled_course(course)
        for course in courses
    ]

    return sorted(
        enrolled_courses,
        key=lambda course: str(course.get("display_name") or "").lower(),
    )


def _find_enrolled_course(
    enrolled_courses: list[dict],
    course_id: int,
) -> dict | None:
    for course in enrolled_courses:
        if course.get("course_id") == course_id:
            return course

    return None


def _require_enrolled_course(
    enrolled_courses: list[dict],
    course_id: int,
) -> dict:
    course = _find_enrolled_course(
        enrolled_courses=enrolled_courses,
        course_id=course_id,
    )

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course was not found for this student.",
        )

    return course


def _build_profile_summary(
    report_row: dict | None,
    freshness_minutes: int,
) -> dict:
    if not report_row:
        return {
            "status": "not_generated",
            "learning_report_id": None,
            "report_key": None,
            "overall_mastery_score": None,
            "generated_at": None,
            "updated_at": None,
            "is_stale": None,
        }

    return {
        "status": "ready",
        "learning_report_id": report_row.get("id"),
        "report_key": report_row.get("report_key"),
        "overall_mastery_score": report_row.get("overall_mastery_score"),
        "generated_at": report_row.get("generated_at"),
        "updated_at": report_row.get("updated_at"),
        "is_stale": _is_profile_stale(
            profile=report_row,
            freshness_minutes=freshness_minutes,
        ),
    }


def _enrich_courses_with_profiles(
    enrolled_courses: list[dict],
    profile_summaries: list[dict],
    freshness_minutes: int,
) -> list[dict]:
    profiles_by_course_id = {
        str(profile.get("course_moodle_id")): profile
        for profile in profile_summaries
        if profile.get("course_moodle_id") is not None
    }

    return [
        {
            **course,
            "profile": _build_profile_summary(
                report_row=profiles_by_course_id.get(str(course["course_id"])),
                freshness_minutes=freshness_minutes,
            ),
        }
        for course in enrolled_courses
    ]


def _resolve_student_from_moodle(
    user: AuthenticatedUser,
    repository: SupabaseLearningReportRepository,
) -> dict:
    client = _build_moodle_client()

    moodle_user = get_user_by_field(
        client=client,
        field="email",
        value=user.email,
    )

    if not moodle_user or moodle_user.get("id") is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No Moodle student could be matched to this login email. "
                "Confirm the student exists in Moodle and Supabase."
            ),
        )

    student = repository.upsert_student_identity(
        moodle_user_id=moodle_user["id"],
        display_name=_moodle_display_name(moodle_user),
        email=user.email,
        auth_user_id=user.id,
    )

    return student


def _resolve_student_for_user(
    user: AuthenticatedUser,
    repository: SupabaseLearningReportRepository,
) -> dict:
    student = repository.get_student_by_auth_user_id(user.id)

    if student:
        if not student.get("email"):
            student = repository.link_student_auth_user(
                student_id=student["id"],
                auth_user_id=user.id,
                email=user.email,
            )

        return student

    student = repository.get_student_by_email(user.email)

    if student:
        existing_auth_user_id = student.get("auth_user_id")

        if existing_auth_user_id and existing_auth_user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This student email is already linked to another login.",
            )

        return repository.link_student_auth_user(
            student_id=student["id"],
            auth_user_id=user.id,
            email=user.email,
        )

    return _resolve_student_from_moodle(
        user=user,
        repository=repository,
    )


def _repository() -> SupabaseLearningReportRepository:
    try:
        return SupabaseLearningReportRepository()
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


def _raise_if_generation_failed(response: dict) -> None:
    if response.get("status") != "failed":
        return

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "status": "failed",
            "source": response.get("source"),
            "job_id": response.get("job_id"),
            "report_key": response.get("report_key"),
            "error_message": response.get(
                "error_message",
                "Learning profile generation failed.",
            ),
        },
    )


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


@app.get("/health")
def health(check_moodle: bool = Query(default=False)) -> dict:
    settings = get_settings()
    checks = {
        "supabase_url": bool(settings.supabase_url),
        "supabase_service_role_key": bool(settings.supabase_service_role_key),
        "moodle_base_url": bool(settings.moodle_base_url),
        "moodle_token": bool(settings.moodle_token),
        "ai_provider": settings.ai_provider,
    }

    if settings.ai_provider == "gemini":
        checks["gemini_api_key"] = bool(settings.gemini_api_key)

    if check_moodle:
        try:
            client = MoodleClient(
                base_url=settings.moodle_base_url,
                token=settings.moodle_token,
                rest_format=settings.moodle_rest_format,
            )
            client.call("core_webservice_get_site_info")
            checks["moodle_reachable"] = True
        except Exception:
            checks["moodle_reachable"] = False

    required_checks = [
        value
        for key, value in checks.items()
        if key != "ai_provider"
    ]

    return {
        "status": "ok" if all(required_checks) else "degraded",
        "checks": checks,
    }


@app.get("/api/me/courses")
def get_my_courses(
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict:
    request_id = _request_id(request)
    start_time = time.perf_counter()
    settings = get_settings()
    repository = _repository()
    student = _resolve_student_for_user(user, repository)
    moodle_user_id = _safe_int(student.get("moodle_user_id"), "moodle_user_id")
    enrolled_courses = _get_enrolled_courses(moodle_user_id)
    profile_summaries = repository.get_course_profile_summaries_for_student(
        student_id=student["id"],
    )
    courses = _enrich_courses_with_profiles(
        enrolled_courses=enrolled_courses,
        profile_summaries=profile_summaries,
        freshness_minutes=settings.api_default_freshness_minutes,
    )

    _log_event(
        "courses_request",
        request_id=request_id,
        auth_user_id=user.id,
        student_id=student.get("id"),
        moodle_user_id=moodle_user_id,
        course_count=len(courses),
        duration_ms=round((time.perf_counter() - start_time) * 1000, 2),
    )

    return {
        "student_id": student.get("id"),
        "moodle_user_id": str(moodle_user_id),
        "courses": courses,
    }


@app.get("/api/me/profile")
def get_my_course_profile(
    request: Request,
    course_id: int,
    course_name: str | None = None,
    assignment_ids: list[int] | None = Query(default=None),
    quiz_ids: list[int] | None = Query(default=None),
    freshness_minutes: int | None = Query(default=None, ge=0),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict:
    request_id = _request_id(request)
    start_time = time.perf_counter()
    settings = get_settings()
    repository = _repository()
    student = _resolve_student_for_user(user, repository)
    moodle_user_id = _safe_int(student.get("moodle_user_id"), "moodle_user_id")
    enrolled_course = _require_enrolled_course(
        enrolled_courses=_get_enrolled_courses(moodle_user_id),
        course_id=course_id,
    )
    resolved_course_name = course_name or enrolled_course.get("display_name")

    response = get_or_generate_student_learning_profile(
        student_user_id=moodle_user_id,
        course_id=course_id,
        student_name=student.get("display_name"),
        course_name=resolved_course_name,
        assignment_ids=assignment_ids,
        quiz_ids=quiz_ids,
        force_refresh=False,
        freshness_minutes=(
            freshness_minutes
            if freshness_minutes is not None
            else settings.api_default_freshness_minutes
        ),
        repository=repository,
    )

    _log_event(
        "profile_request",
        request_id=request_id,
        auth_user_id=user.id,
        student_id=student.get("id"),
        moodle_user_id=moodle_user_id,
        course_id=course_id,
        job_id=response.get("job_id"),
        report_key=response.get("report_key"),
        status=response.get("status"),
        source=response.get("source"),
        duration_ms=round((time.perf_counter() - start_time) * 1000, 2),
    )

    _raise_if_generation_failed(response)
    return response


@app.post("/api/me/profile/refresh")
def refresh_my_course_profile(
    request: Request,
    payload: ProfileRefreshRequest,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict:
    request_id = _request_id(request)
    start_time = time.perf_counter()
    repository = _repository()
    student = _resolve_student_for_user(user, repository)
    moodle_user_id = _safe_int(student.get("moodle_user_id"), "moodle_user_id")
    enrolled_course = _require_enrolled_course(
        enrolled_courses=_get_enrolled_courses(moodle_user_id),
        course_id=payload.course_id,
    )
    resolved_course_name = payload.course_name or enrolled_course.get("display_name")

    response = get_or_generate_student_learning_profile(
        student_user_id=moodle_user_id,
        course_id=payload.course_id,
        student_name=student.get("display_name"),
        course_name=resolved_course_name,
        assignment_ids=payload.assignment_ids,
        quiz_ids=payload.quiz_ids,
        assessment_weights=payload.assessment_weights,
        explicit_assignment_mappings=payload.explicit_assignment_mappings,
        explicit_quiz_mappings=payload.explicit_quiz_mappings,
        force_refresh=True,
        repository=repository,
    )

    _log_event(
        "profile_refresh",
        request_id=request_id,
        auth_user_id=user.id,
        student_id=student.get("id"),
        moodle_user_id=moodle_user_id,
        course_id=payload.course_id,
        job_id=response.get("job_id"),
        report_key=response.get("report_key"),
        status=response.get("status"),
        source=response.get("source"),
        duration_ms=round((time.perf_counter() - start_time) * 1000, 2),
    )

    _raise_if_generation_failed(response)
    return response


@app.get("/api/jobs/{job_id}")
def get_my_job_status(
    job_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> dict:
    repository = _repository()
    student = _resolve_student_for_user(user, repository)
    status_response = get_report_generation_status(
        job_id=job_id,
        repository=repository,
    )

    if status_response.get("status") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching report generation job was found.",
        )

    if status_response.get("student_id") != student.get("id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching report generation job was found.",
        )

    return status_response
