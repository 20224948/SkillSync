from moodle.normalisers.quiz_normaliser import normalise_student_quiz_context


def _competencies_response() -> dict:
    return {
        "competencies": [
            {
                "competency": {
                    "id": 101,
                    "idnumber": "IT101-SILO1",
                    "shortname": "SILO 1",
                    "description": "Explain foundational IT concepts.",
                }
            }
        ]
    }


def _quiz() -> dict:
    return {
        "id": 12,
        "course": 2,
        "coursemodule": 34,
        "name": "Quiz 1",
        "intro": "<p>Foundational IT concepts</p>",
        "grade": 10,
    }


def _attempt(state: str) -> dict:
    return {
        "id": 9001,
        "attempt": 1,
        "uniqueid": 8001,
        "state": state,
        "sumgrades": 8,
        "timestart": 100,
        "timefinish": 200,
        "timemodified": 210,
    }


def _context_for_state(state: str, has_grade: bool = True) -> dict:
    return normalise_student_quiz_context(
        quiz=_quiz(),
        attempts_response={"attempts": [_attempt(state)]},
        best_grade_response={
            "hasgrade": has_grade,
            "grade": 8 if has_grade else None,
        },
        competencies_response=_competencies_response(),
        student_user_id=9,
        course_id=2,
    )


def test_finished_attempt_is_valid() -> None:
    context = _context_for_state("finished")

    assert context["is_valid_for_mastery"] is True
    assert context["best_grade"]["grade_percent"] == 80
    assert context["selected_attempt"]["attempt_id"] == 9001
    assert context["competency_mappings"][0]["silo_id"] == "IT101-SILO1"


def test_submitted_attempt_is_valid_when_grade_exists() -> None:
    context = _context_for_state("submitted")

    assert context["is_valid_for_mastery"] is True


def test_unfinished_attempt_is_skipped() -> None:
    context = _context_for_state("inprogress")

    assert context["is_valid_for_mastery"] is False
    assert "no_completed_attempt" in context["skip_reasons"]


def test_notstarted_attempt_is_skipped() -> None:
    context = _context_for_state("notstarted")

    assert context["is_valid_for_mastery"] is False
    assert "no_completed_attempt" in context["skip_reasons"]


def test_missing_grade_is_skipped() -> None:
    context = _context_for_state("finished", has_grade=False)

    assert context["is_valid_for_mastery"] is False
    assert "missing_best_grade" in context["skip_reasons"]


def test_explicit_mappings_work_without_moodle_competencies() -> None:
    context = normalise_student_quiz_context(
        quiz=_quiz(),
        attempts_response={"attempts": [_attempt("finished")]},
        best_grade_response={"hasgrade": True, "grade": 8},
        competencies_response=[],
        student_user_id=9,
        course_id=2,
        explicit_mappings={
            "12": [
                {"competency_id": "SILO1", "coverage_weight": 0.25},
                {"competency_id": "SILO2", "coverage_weight": 0.75},
            ]
        },
    )

    assert context["is_valid_for_mastery"] is True
    assert len(context["competency_mappings"]) == 2
    assert context["competency_mappings"][0]["coverage_weight"] == 0.25
    assert context["competency_mappings"][1]["coverage_weight"] == 0.75


if __name__ == "__main__":
    test_finished_attempt_is_valid()
    test_submitted_attempt_is_valid_when_grade_exists()
    test_unfinished_attempt_is_skipped()
    test_notstarted_attempt_is_skipped()
    test_missing_grade_is_skipped()
    test_explicit_mappings_work_without_moodle_competencies()
    print("Quiz normaliser tests passed.")
