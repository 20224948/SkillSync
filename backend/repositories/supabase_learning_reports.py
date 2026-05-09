from __future__ import annotations

from urllib.parse import quote

import requests

from config import get_settings


class SupabaseLearningReportRepository:
    """
    Stores SkillSync learning reports in Supabase using the PostgREST API.

    This keeps persistence separate from Moodle, mastery, and AI logic. The
    service layer builds a report; this repository only knows how to save it.
    """

    def __init__(
        self,
        supabase_url: str | None = None,
        service_role_key: str | None = None,
    ):
        settings = get_settings()

        self.supabase_url = (supabase_url or settings.supabase_url or "").rstrip("/")
        self.service_role_key = service_role_key or settings.supabase_service_role_key

        if not self.supabase_url:
            raise ValueError("SUPABASE_URL is missing from .env.")

        if not self.service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is missing from .env.")

        self.rest_url = f"{self.supabase_url}/rest/v1"

    def _headers(self, prefer: str | None = None) -> dict:
        """
        Builds Supabase REST headers.

        The service role key must only be used in backend/server-side code.
        """

        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }

        if prefer:
            headers["Prefer"] = prefer

        return headers

    def _text_or_none(self, value: object) -> str | None:
        """
        Converts optional external IDs to text without storing the string "None".
        """

        if value is None:
            return None

        return str(value)

    def _request(
        self,
        method: str,
        path: str,
        json_body: dict | list | None = None,
        prefer: str | None = None,
    ) -> dict | list | None:
        """
        Sends one request to Supabase and raises helpful errors.
        """

        response = requests.request(
            method=method,
            url=f"{self.rest_url}/{path}",
            headers=self._headers(prefer=prefer),
            json=json_body,
            timeout=60,
        )

        if not response.ok:
            raise RuntimeError(
                f"Supabase request failed: {method} {path} "
                f"returned {response.status_code}: {response.text}"
            )

        if not response.text:
            return None

        return response.json()

    def _delete_child_rows(self, table_name: str, learning_report_id: str) -> None:
        """
        Clears child rows before reinserting the latest report details.
        """

        encoded_id = quote(learning_report_id, safe="")
        self._request(
            method="DELETE",
            path=f"{table_name}?learning_report_id=eq.{encoded_id}",
        )

    def upsert_student_identity(
        self,
        moodle_user_id: int | str,
        display_name: str | None = None,
        email: str | None = None,
        auth_user_id: str | None = None,
    ) -> dict:
        """
        Creates or updates a student row by Moodle user ID.
        """

        moodle_user_id_text = str(moodle_user_id)

        if not moodle_user_id_text or moodle_user_id_text == "None":
            raise ValueError("Cannot save student because Moodle user ID is missing.")

        row = {
            "moodle_user_id": moodle_user_id_text,
        }

        if display_name is not None:
            row["display_name"] = display_name

        if email:
            row["email"] = email.strip().lower()

        if auth_user_id:
            row["auth_user_id"] = auth_user_id

        rows = self._request(
            method="POST",
            path="students?on_conflict=moodle_user_id",
            json_body=row,
            prefer="resolution=merge-duplicates,return=representation",
        )

        if not rows:
            raise RuntimeError("Supabase did not return the saved student row.")

        return rows[0]

    def get_student_by_auth_user_id(self, auth_user_id: str) -> dict | None:
        """
        Gets the student linked to the authenticated Supabase user.
        """

        encoded_auth_user_id = quote(auth_user_id, safe="")

        rows = self._request(
            method="GET",
            path=(
                "students"
                f"?auth_user_id=eq.{encoded_auth_user_id}"
                "&select=*"
                "&limit=1"
            ),
        )

        if not rows:
            return None

        return rows[0]

    def get_student_by_email(self, email: str) -> dict | None:
        """
        Gets a student by email using case-insensitive matching.
        """

        encoded_email = quote(email.strip().lower(), safe="")

        rows = self._request(
            method="GET",
            path=(
                "students"
                f"?email=ilike.{encoded_email}"
                "&select=*"
                "&limit=1"
            ),
        )

        if not rows:
            return None

        return rows[0]

    def link_student_auth_user(
        self,
        student_id: str,
        auth_user_id: str,
        email: str | None = None,
    ) -> dict:
        """
        Links a Supabase Auth user to a student row.
        """

        encoded_student_id = quote(student_id, safe="")
        update = {
            "auth_user_id": auth_user_id,
        }

        if email:
            update["email"] = email.strip().lower()

        rows = self._request(
            method="PATCH",
            path=f"students?id=eq.{encoded_student_id}",
            json_body=update,
            prefer="return=representation",
        )

        if not rows:
            raise RuntimeError("Supabase did not return the linked student row.")

        return rows[0]

    def _upsert_student(self, report: dict) -> dict:
        """
        Creates or updates the student row this report belongs to.

        The Moodle user ID is the stable external identifier. The generated UUID
        is used as the internal Supabase foreign key.
        """

        student = report.get("student", {})
        return self.upsert_student_identity(
            moodle_user_id=student.get("moodle_user_id"),
            display_name=student.get("name"),
        )

    def get_learning_report_by_key(self, report_key: str) -> dict | None:
        """
        Gets the latest stored report for a stable student/course/assignment key.

        report_key is unique, so this returns either one row or None.
        """

        encoded_key = quote(report_key, safe="")

        rows = self._request(
            method="GET",
            path=(
                "learning_reports"
                f"?report_key=eq.{encoded_key}"
                "&select=*"
                "&limit=1"
            ),
        )

        if not rows:
            return None

        return rows[0]

    def get_course_profile_summaries_for_student(self, student_id: str) -> list[dict]:
        """
        Gets stored course-level profile summaries for one authenticated student.

        These rows are used to enrich live Moodle enrolments without loading the
        full report JSON or triggering new report generation.
        """

        encoded_student_id = quote(student_id, safe="")

        rows = self._request(
            method="GET",
            path=(
                "learning_reports"
                f"?student_id=eq.{encoded_student_id}"
                "&report_type=eq.course_learning_profile"
                "&select="
                "id,"
                "report_key,"
                "report_type,"
                "course_moodle_id,"
                "course_name,"
                "overall_mastery_score,"
                "generated_at,"
                "updated_at"
                "&order=generated_at.desc"
            ),
        )

        return rows or []

    def create_report_generation_job(
        self,
        report_key: str,
        student_moodle_user_id: int | str,
        course_id: int | str,
        assignment_id: int | str | None = None,
        student_name: str | None = None,
        force_refresh: bool = False,
        source: str = "backend_request",
        report_type: str = "assignment_learning_report",
    ) -> dict:
        """
        Creates a generation job row for backend/API orchestration.

        The current implementation runs the job synchronously, but the same row
        can support a background worker later.
        """

        student = self.upsert_student_identity(
            moodle_user_id=student_moodle_user_id,
            display_name=student_name,
        )

        rows = self._request(
            method="POST",
            path="report_generation_jobs",
            json_body={
                "report_key": report_key,
                "student_id": student["id"],
                "student_moodle_user_id": str(student_moodle_user_id),
                "course_moodle_id": str(course_id),
                "assignment_moodle_id": (
                    str(assignment_id)
                    if assignment_id is not None
                    else None
                ),
                "report_type": report_type,
                "status": "pending",
                "source": source,
                "force_refresh": force_refresh,
            },
            prefer="return=representation",
        )

        if not rows:
            raise RuntimeError("Supabase did not return the created generation job.")

        return rows[0]

    def update_report_generation_job(
        self,
        job_id: str,
        status: str,
        learning_report_id: str | None = None,
        error_message: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        source: str | None = None,
    ) -> dict:
        """
        Updates a generation job row and returns the updated job.
        """

        job_update = {
            "status": status,
        }

        if learning_report_id is not None:
            job_update["learning_report_id"] = learning_report_id

        if error_message is not None:
            job_update["error_message"] = error_message

        if started_at is not None:
            job_update["started_at"] = started_at

        if completed_at is not None:
            job_update["completed_at"] = completed_at

        if source is not None:
            job_update["source"] = source

        if status == "ready":
            job_update["error_message"] = None

        encoded_job_id = quote(job_id, safe="")

        rows = self._request(
            method="PATCH",
            path=f"report_generation_jobs?id=eq.{encoded_job_id}",
            json_body=job_update,
            prefer="return=representation",
        )

        if not rows:
            raise RuntimeError("Supabase did not return the updated generation job.")

        return rows[0]

    def get_report_generation_job(self, job_id: str) -> dict | None:
        """
        Gets one report generation job by ID.
        """

        encoded_job_id = quote(job_id, safe="")

        rows = self._request(
            method="GET",
            path=(
                "report_generation_jobs"
                f"?id=eq.{encoded_job_id}"
                "&select=*"
                "&limit=1"
            ),
        )

        if not rows:
            return None

        return rows[0]

    def get_latest_report_generation_job(self, report_key: str) -> dict | None:
        """
        Gets the latest generation job for a report key.
        """

        encoded_report_key = quote(report_key, safe="")

        rows = self._request(
            method="GET",
            path=(
                "report_generation_jobs"
                f"?report_key=eq.{encoded_report_key}"
                "&select=*"
                "&order=created_at.desc"
                "&limit=1"
            ),
        )

        if not rows:
            return None

        return rows[0]

    def _save_competency_mastery_rows(
        self,
        learning_report_id: str,
        report: dict,
    ) -> None:
        """
        Saves one row per calculated competency/SILO mastery result.
        """

        mastery_items = report.get("mastery_report", {}).get("silo_mastery", [])

        rows = [
            {
                "learning_report_id": learning_report_id,
                "competency_id": item.get("silo_id"),
                "title": item.get("title"),
                "description": item.get("description"),
                "mastery_score": item.get("mastery_score"),
                "confidence": item.get("confidence"),
                "evidence_count": item.get("evidence_count"),
                "total_evidence_weight": item.get("total_evidence_weight"),
                "evidence": item.get("evidence", []),
            }
            for item in mastery_items
        ]

        if rows:
            self._request(
                method="POST",
                path="competency_mastery",
                json_body=rows,
                prefer="return=minimal",
            )

    def _save_student_evidence_rows(
        self,
        learning_report_id: str,
        report: dict,
    ) -> None:
        """
        Saves evidence rows used by the mastery engine.
        """

        rows = []

        if "student_evidence" in report:
            for item in report.get("student_evidence", []):
                rows.append(
                    {
                        "learning_report_id": learning_report_id,
                        "source_type": item.get("source_type"),
                        "assignment_moodle_id": self._text_or_none(
                            item.get("assignment_moodle_id")
                        ),
                        "quiz_moodle_id": self._text_or_none(
                            item.get("quiz_moodle_id")
                        ),
                        "quiz_attempt_id": self._text_or_none(
                            item.get("quiz_attempt_id")
                        ),
                        "course_module_id": self._text_or_none(
                            item.get("course_module_id")
                        ),
                        "criterion_id": self._text_or_none(item.get("criterion_id")),
                        "competency_id": item.get("competency_id"),
                        "competency_code": item.get("competency_code"),
                        "competency_name": item.get("competency_name"),
                        "score": item.get("score"),
                        "max_score": item.get("max_score"),
                        "normalised_score": item.get("normalised_score"),
                        "feedback": item.get("feedback"),
                        "mapping_source": item.get("mapping_source"),
                        "evidence": item.get("evidence", {}),
                    }
                )

            if rows:
                self._request(
                    method="POST",
                    path="student_evidence",
                    json_body=rows,
                    prefer="return=minimal",
                )

            return

        evidence_by_criterion = {
            str(item.get("criterion_id")): item
            for item in report.get("ai_learning_support_input", {}).get("evidence_used", [])
        }

        for item in report.get("student_competency_evidence", []):
            criterion_id = str(item.get("criterion_id"))
            enriched_evidence = evidence_by_criterion.get(criterion_id, {})

            rows.append(
                {
                    "learning_report_id": learning_report_id,
                    "source_type": "assignment_rubric",
                    "assignment_moodle_id": str(item.get("assignment_id")),
                    "quiz_moodle_id": None,
                    "quiz_attempt_id": None,
                    "course_module_id": None,
                    "criterion_id": criterion_id,
                    "competency_id": item.get("competency_id"),
                    "competency_code": enriched_evidence.get("competency_code"),
                    "competency_name": enriched_evidence.get("competency_name"),
                    "score": item.get("score"),
                    "max_score": item.get("max_score"),
                    "normalised_score": item.get("normalised_score"),
                    "feedback": item.get("feedback"),
                    "mapping_source": item.get("mapping_source"),
                    "evidence": enriched_evidence,
                }
            )

        if rows:
            self._request(
                method="POST",
                path="student_evidence",
                json_body=rows,
                prefer="return=minimal",
            )

    def _save_ai_quiz_question_groups(
        self,
        learning_report_id: str,
        report: dict,
    ) -> list[dict]:
        """
        Saves generated MCQ groups separately for easier frontend rendering.
        """

        question_groups = report.get("ai_feedback", {}).get("generated_quiz_questions", [])

        rows = [
            {
                "learning_report_id": learning_report_id,
                "weak_area": group.get("weak_area"),
                "questions": group.get("questions", []),
            }
            for group in question_groups
        ]

        if not rows:
            return []

        saved_groups = self._request(
            method="POST",
            path="ai_quiz_question_groups",
            json_body=rows,
            prefer="return=representation",
        )

        return saved_groups or []

    def _save_ai_quiz_questions(
        self,
        learning_report_id: str,
        saved_question_groups: list[dict],
    ) -> None:
        """
        Saves one row per generated MCQ.

        The original group JSON is still stored in ai_quiz_question_groups and
        learning_reports.ai_feedback. These normalized rows are for easier
        frontend rendering and querying.
        """

        rows = []

        for group in saved_question_groups:
            question_group_id = group.get("id")
            weak_area = group.get("weak_area")
            questions = group.get("questions", [])

            for index, question in enumerate(questions, start=1):
                rows.append(
                    {
                        "question_group_id": question_group_id,
                        "learning_report_id": learning_report_id,
                        "weak_area": weak_area,
                        "question_number": index,
                        "question_text": question.get("question"),
                        "choice_1": question.get("choice_1"),
                        "choice_2": question.get("choice_2"),
                        "choice_3": question.get("choice_3"),
                        "correct_answer": question.get("correct_answer"),
                        "explanation": question.get("explanation"),
                        "question_payload": question,
                    }
                )

        if rows:
            self._request(
                method="POST",
                path="ai_quiz_questions",
                json_body=rows,
                prefer="return=minimal",
            )

    def _save_ai_recommendations(
        self,
        learning_report_id: str,
        report: dict,
    ) -> None:
        """
        Saves AI recommendations separately for frontend cards/lists.
        """

        recommendations = report.get("ai_feedback", {}).get("recommendations", [])

        rows = [
            {
                "learning_report_id": learning_report_id,
                "title": recommendation.get("title"),
                "related_area": recommendation.get("related_area"),
                "reason": recommendation.get("reason"),
                "action": recommendation.get("action"),
                "recommendation": recommendation,
            }
            for recommendation in recommendations
        ]

        if rows:
            self._request(
                method="POST",
                path="ai_recommendations",
                json_body=rows,
                prefer="return=minimal",
            )

    def save_learning_report(self, report: dict) -> dict:
        """
        Upserts the main learning report and replaces its child rows.
        """

        saved_student = self._upsert_student(report)

        student = report.get("student", {})
        course = report.get("course", {})
        assessment = report.get("assessment", {})
        metadata = report.get("metadata", {})
        mastery_report = report.get("mastery_report", {})
        report_type = (
            report.get("report_type")
            or report.get("source", {}).get("data_type")
            or "assignment_learning_report"
        )
        evidence_rows = report.get(
            "student_evidence",
            report.get("student_competency_evidence", []),
        )

        learning_report_row = {
            "report_key": report.get("report_key"),
            "report_type": report_type,
            "schema_version": report.get("schema_version"),
            "student_id": saved_student["id"],
            "student_moodle_user_id": str(student.get("moodle_user_id")),
            "student_name": student.get("name"),
            "course_moodle_id": str(course.get("course_id")),
            "course_name": course.get("course_name"),
            "assignment_moodle_id": self._text_or_none(
                assessment.get("assignment_id")
            ),
            "assignment_name": assessment.get("name"),
            "course_module_id": self._text_or_none(
                assessment.get("course_module_id")
            ),
            "included_assessments": report.get("included_assessments", []),
            "overall_mastery_score": mastery_report.get("overall_mastery_score"),
            "weakest_competencies": report.get("calculated_weak_areas", []),
            "mastery_report": mastery_report,
            "ai_feedback": report.get("ai_feedback", {}),
            "evidence": evidence_rows,
            "full_report": report,
            "ai_provider": metadata.get("ai_provider"),
            "ai_model": metadata.get("ai_model"),
            "generated_at": report.get("generated_at"),
        }

        saved_rows = self._request(
            method="POST",
            path="learning_reports?on_conflict=report_key",
            json_body=learning_report_row,
            prefer="resolution=merge-duplicates,return=representation",
        )

        if not saved_rows:
            raise RuntimeError("Supabase did not return the saved learning report row.")

        saved_report = saved_rows[0]
        learning_report_id = saved_report["id"]

        for table_name in [
            "competency_mastery",
            "student_evidence",
            "ai_quiz_questions",
            "ai_quiz_question_groups",
            "ai_recommendations",
        ]:
            self._delete_child_rows(
                table_name=table_name,
                learning_report_id=learning_report_id,
            )

        self._save_competency_mastery_rows(
            learning_report_id=learning_report_id,
            report=report,
        )
        self._save_student_evidence_rows(
            learning_report_id=learning_report_id,
            report=report,
        )
        saved_question_groups = self._save_ai_quiz_question_groups(
            learning_report_id=learning_report_id,
            report=report,
        )
        self._save_ai_quiz_questions(
            learning_report_id=learning_report_id,
            saved_question_groups=saved_question_groups,
        )
        self._save_ai_recommendations(
            learning_report_id=learning_report_id,
            report=report,
        )

        return {
            "learning_report_id": learning_report_id,
            "student_id": saved_student["id"],
            "report_key": saved_report.get("report_key"),
            "saved_to_supabase": True,
        }
