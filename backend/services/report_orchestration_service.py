from __future__ import annotations

from datetime import UTC, datetime, timedelta

from config import get_settings
from repositories.supabase_learning_reports import SupabaseLearningReportRepository
from services.learning_report_service import (
    build_course_profile_key,
    build_report_key,
    generate_learning_report_for_assignment,
    generate_student_learning_profile,
)


def _now_iso() -> str:
    """
    Returns an ISO timestamp for job status updates.
    """

    return datetime.now(UTC).isoformat()


def _safe_error_message(error: Exception) -> str:
    """
    Redacts configured secrets from errors before storing or returning them.
    """

    message = str(error)
    settings = get_settings()

    for secret in [
        settings.moodle_token,
        settings.gemini_api_key,
        settings.supabase_service_role_key,
    ]:
        if secret:
            message = message.replace(secret, "[redacted]")

    return message


def _parse_timestamp(value: str | None) -> datetime | None:
    """
    Parses timestamps returned by Supabase/Postgres.
    """

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _is_report_fresh(
    report_row: dict | None,
    freshness_minutes: int,
) -> bool:
    """
    Checks whether a stored report can be reused.

    This avoids running Moodle + AI work every time the frontend opens a page.
    """

    if not report_row:
        return False

    generated_at = _parse_timestamp(report_row.get("generated_at"))

    if generated_at is None:
        return False

    oldest_allowed = datetime.now(UTC) - timedelta(minutes=freshness_minutes)

    return generated_at >= oldest_allowed


def _build_existing_report_response(
    report_row: dict,
    report_key: str,
) -> dict:
    """
    Builds the backend response when a fresh stored report is reused.
    """

    full_report = report_row.get("full_report") or {}

    return {
        "status": "ready",
        "source": "existing_report",
        "job_id": None,
        "learning_report_id": report_row.get("id"),
        "student_id": report_row.get("student_id"),
        "report_type": report_row.get("report_type"),
        "report_key": report_key,
        "overall_mastery_score": report_row.get("overall_mastery_score"),
        "generated_at": report_row.get("generated_at"),
        "report": full_report,
    }


def get_or_generate_learning_report(
    student_user_id: int,
    course_id: int,
    assignment_id: int,
    student_name: str | None = None,
    course_name: str | None = None,
    assignment_weight_percent: float = 100.0,
    explicit_mappings: dict | list | None = None,
    force_refresh: bool = False,
    freshness_minutes: int = 1440, 
    repository: SupabaseLearningReportRepository | None = None,
    raise_on_error: bool = False,
) -> dict:
    """
    Backend-facing orchestration entry point.

    This is the function Baqir's backend can call.

    Behaviour:
    - Reuse a fresh report unless force_refresh=True.
    - If missing/stale/forced, create a generation job.
    - Run the SkillSync AI component synchronously for now.
    - Save the report to Supabase.
    - Mark the job ready or failed.

    The job table makes the flow compatible with a future background worker.
    """

    report_key = build_report_key(
        student_user_id=student_user_id,
        course_id=course_id,
        assignment_id=assignment_id,
    )

    repository = repository or SupabaseLearningReportRepository()

    existing_report = repository.get_learning_report_by_key(report_key)

    if not force_refresh and _is_report_fresh(
        report_row=existing_report,
        freshness_minutes=freshness_minutes,
    ):
        return _build_existing_report_response(
            report_row=existing_report,
            report_key=report_key,
        )

    job = repository.create_report_generation_job(
        report_key=report_key,
        student_moodle_user_id=student_user_id,
        course_id=course_id,
        assignment_id=assignment_id,
        student_name=student_name,
        force_refresh=force_refresh,
    )

    try:
        repository.update_report_generation_job(
            job_id=job["id"],
            status="running",
            started_at=_now_iso(),
        )

        report = generate_learning_report_for_assignment(
            student_user_id=student_user_id,
            course_id=course_id,
            assignment_id=assignment_id,
            student_name=student_name,
            course_name=course_name,
            assignment_weight_percent=assignment_weight_percent,
            explicit_mappings=explicit_mappings,
        )

        save_result = repository.save_learning_report(report)

        completed_job = repository.update_report_generation_job(
            job_id=job["id"],
            status="ready",
            learning_report_id=save_result["learning_report_id"],
            completed_at=_now_iso(),
            source="generated_new_report",
        )

        return {
            "status": "ready",
            "source": "generated_new_report",
            "job_id": completed_job.get("id"),
            "learning_report_id": save_result["learning_report_id"],
            "student_id": save_result["student_id"],
            "report_key": report_key,
            "overall_mastery_score": (
                report.get("mastery_report", {})
                .get("overall_mastery_score")
            ),
            "generated_at": report.get("generated_at"),
            "report": report,
        }

    except Exception as error:
        error_message = _safe_error_message(error)

        failed_job = repository.update_report_generation_job(
            job_id=job["id"],
            status="failed",
            error_message=error_message,
            completed_at=_now_iso(),
            source="generation_failed",
        )

        if raise_on_error:
            raise

        return {
            "status": "failed",
            "source": "generation_failed",
            "job_id": failed_job.get("id"),
            "learning_report_id": None,
            "student_id": failed_job.get("student_id"),
            "report_key": report_key,
            "overall_mastery_score": None,
            "generated_at": None,
            "error_message": error_message,
            "report": None,
        }


def get_or_generate_student_learning_profile(
    student_user_id: int,
    course_id: int,
    student_name: str | None = None,
    course_name: str | None = None,
    assignment_ids: list[int] | None = None,
    quiz_ids: list[int] | None = None,
    assessment_weights: dict | None = None,
    explicit_assignment_mappings: dict | list | None = None,
    explicit_quiz_mappings: dict | list | None = None,
    force_refresh: bool = False,
    freshness_minutes: int = 1440,
    repository: SupabaseLearningReportRepository | None = None,
    raise_on_error: bool = False,
) -> dict:
    """
    Backend-facing entry point for course-level mastery profiles.

    This combines assignment rubric evidence and Moodle quiz grade evidence into
    one student/course mastery report.
    """

    report_key = build_course_profile_key(
        student_user_id=student_user_id,
        course_id=course_id,
    )

    repository = repository or SupabaseLearningReportRepository()

    existing_report = repository.get_learning_report_by_key(report_key)

    if not force_refresh and _is_report_fresh(
        report_row=existing_report,
        freshness_minutes=freshness_minutes,
    ):
        return _build_existing_report_response(
            report_row=existing_report,
            report_key=report_key,
        )

    job = repository.create_report_generation_job(
        report_key=report_key,
        student_moodle_user_id=student_user_id,
        course_id=course_id,
        assignment_id=None,
        student_name=student_name,
        force_refresh=force_refresh,
        report_type="course_learning_profile",
    )

    try:
        repository.update_report_generation_job(
            job_id=job["id"],
            status="running",
            started_at=_now_iso(),
        )

        report = generate_student_learning_profile(
            student_user_id=student_user_id,
            course_id=course_id,
            student_name=student_name,
            course_name=course_name,
            assignment_ids=assignment_ids,
            quiz_ids=quiz_ids,
            assessment_weights=assessment_weights,
            explicit_assignment_mappings=explicit_assignment_mappings,
            explicit_quiz_mappings=explicit_quiz_mappings,
        )

        save_result = repository.save_learning_report(report)

        completed_job = repository.update_report_generation_job(
            job_id=job["id"],
            status="ready",
            learning_report_id=save_result["learning_report_id"],
            completed_at=_now_iso(),
            source="generated_new_profile",
        )

        return {
            "status": "ready",
            "source": "generated_new_profile",
            "job_id": completed_job.get("id"),
            "learning_report_id": save_result["learning_report_id"],
            "student_id": save_result["student_id"],
            "report_key": report_key,
            "overall_mastery_score": (
                report.get("mastery_report", {})
                .get("overall_mastery_score")
            ),
            "generated_at": report.get("generated_at"),
            "report": report,
        }

    except Exception as error:
        error_message = _safe_error_message(error)

        failed_job = repository.update_report_generation_job(
            job_id=job["id"],
            status="failed",
            error_message=error_message,
            completed_at=_now_iso(),
            source="generation_failed",
        )

        if raise_on_error:
            raise

        return {
            "status": "failed",
            "source": "generation_failed",
            "job_id": failed_job.get("id"),
            "learning_report_id": None,
            "student_id": failed_job.get("student_id"),
            "report_key": report_key,
            "overall_mastery_score": None,
            "generated_at": None,
            "error_message": error_message,
            "report": None,
        }


def get_report_generation_status(
    job_id: str | None = None,
    student_user_id: int | None = None,
    course_id: int | None = None,
    assignment_id: int | None = None,
    report_type: str = "assignment_learning_report",
    repository: SupabaseLearningReportRepository | None = None,
) -> dict:
    """
    Backend-facing status lookup for report generation jobs.

    A backend API can call this for:
    - GET /learning-report/jobs/{job_id}
    - or "latest job for this student/course/assignment"
    """

    repository = repository or SupabaseLearningReportRepository()

    if job_id:
        job = repository.get_report_generation_job(job_id)
    else:
        missing_fields = [
            name for name, value in [
                ("student_user_id", student_user_id),
                ("course_id", course_id),
            ]
            if value is None
        ]

        if report_type == "assignment_learning_report" and assignment_id is None:
            missing_fields.append("assignment_id")

        if missing_fields:
            raise ValueError(
                "Provide job_id or the fields needed to build the report key. "
                f"Missing: {', '.join(missing_fields)}"
            )

        if assignment_id is None or report_type == "course_learning_profile":
            report_key = build_course_profile_key(
                student_user_id=student_user_id,
                course_id=course_id,
            )
        else:
            report_key = build_report_key(
                student_user_id=student_user_id,
                course_id=course_id,
                assignment_id=assignment_id,
            )

        job = repository.get_latest_report_generation_job(report_key)

    if not job:
        return {
            "status": "not_found",
            "job_id": job_id,
            "report_key": None,
            "learning_report_id": None,
            "error_message": "No matching report generation job was found.",
        }

    return {
        "status": job.get("status"),
        "job_id": job.get("id"),
        "report_key": job.get("report_key"),
        "student_id": job.get("student_id"),
        "student_moodle_user_id": job.get("student_moodle_user_id"),
        "course_moodle_id": job.get("course_moodle_id"),
        "assignment_moodle_id": job.get("assignment_moodle_id"),
        "report_type": job.get("report_type"),
        "learning_report_id": job.get("learning_report_id"),
        "source": job.get("source"),
        "force_refresh": job.get("force_refresh"),
        "error_message": job.get("error_message"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }
