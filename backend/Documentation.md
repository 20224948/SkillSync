
# SkillSync AI, Moodle Integration, and Mastery Model Documentation

Backend/frontend handoff guide:

```text
docs/backend_frontend_guide.md
```

Use that guide when wiring Mark's frontend UI to the hosted FastAPI backend and
the report orchestration pipeline.

## 1. Project Purpose

The SkillSync AI component is designed to retrieve student learning evidence from Moodle, calculate learning mastery against subject learning outcomes, and generate personalised AI feedback.

The current implementation supports:

```text
Moodle API integration
Assignment submission extraction
Assignment grade extraction
Feedback comment extraction
Rubric evidence extraction
Moodle quiz grade extraction
Course-level learning profile generation
AI-ready input generation
AI feedback generation
SILO-based Mastery Model calculation
Supabase report storage and job orchestration
Provider-flexible AI generation using Gemini or Ollama
```

The key design principle is:

```text
Python calculates learning evidence and mastery scores.
The AI explains the evidence and generates personalised learning support.
```

This prevents the AI from inventing grades, rubric scores, or mastery results.

---

# 2. Current High-Level Architecture

The current system has four major layers:

```text
1. Moodle API Layer
   Connects to Moodle and retrieves raw course, user, assignment, grade, feedback, and rubric data.

2. Normaliser Layer
   Converts raw Moodle responses into clean Python dictionaries.

3. Mastery Model Layer
   Calculates SILO-based mastery scores from assessment evidence.

4. AI Layer
   Sends clean learning evidence to Gemini or Ollama and receives structured AI feedback.
```

Assignment feedback flow:

```text
Moodle
  ↓
Moodle API client
  ↓
Assignment normaliser
  ↓
AI input builder
  ↓
AI provider
  ↓
Structured feedback JSON
```

Course-level mastery flow:

```text
Moodle assignment rubric evidence
Moodle quiz grade evidence
  ↓
Assignment and quiz normalisers
  ↓
Mastery input builder
  ↓
Mastery Model
  ↓
Course-level SILO mastery report
  |
AI provider explains the calculated result
  |
Supabase learning report storage
```

---

# 3. Current Project Structure

Your project structure should look roughly like this:

```text
SkillSync-AI/
│
├── .env
├── .gitignore
├── config.py
├── test_ai.py
├── test_mastery_ai.py
│
├── api/
│   ├── __init__.py
│   ├── auth.py
│   └── main.py
│
├── ai/
│   ├── __init__.py
│   ├── base.py
│   ├── gemini_provider.py
│   ├── ollama_provider.py
│   ├── prompts.py
│   ├── provider_factory.py
│   └── schemas.py
│
├── mastery/
│   ├── __init__.py
│   ├── mastery_model.py
│   └── mock_data.py
│
├── moodle/
│   ├── __init__.py
│   ├── client.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── courses.py
│   │   ├── assignments.py
│   │   └── rubrics.py
│   │
│   └── normalisers/
│       ├── __init__.py
│       ├── assignment_normaliser.py
│       ├── ai_input_builder.py
│       └── mastery_input_builder.py
│
├── services/
│   ├── __init__.py
│   └── assignment_feedback_service.py
│
└── scripts/
    ├── __init__.py
    ├── test_moodle_connection.py
    ├── inspect_moodle_users_courses.py
    ├── inspect_moodle_course_assignments.py
    ├── inspect_assignment_submission.py
    ├── inspect_assignment_rubric.py
    ├── test_assignment_normaliser.py
    ├── test_assignment_ai_input.py
    ├── test_assignment_feedback_service.py
    └── test_mastery_from_assignment_ai_input.py
```

---

# 4. Environment Configuration

The project uses `.env` for configuration.

Example `.env`:

```env
# AI provider selection
AI_PROVIDER=gemini

# Ollama settings
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=600

# Gemini settings
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_OUTPUT_TOKENS=4096
GEMINI_THINKING_BUDGET=0

# Moodle settings
MOODLE_BASE_URL=https://moodle.skillsynch.org
MOODLE_TOKEN=your_moodle_webservice_token_here
MOODLE_REST_FORMAT=json

# Supabase backend settings
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_backend_service_role_key

# API settings
CORS_ALLOWED_ORIGINS=*
API_DEFAULT_FRESHNESS_MINUTES=1440
```

Important rules:

```text
Never commit .env to GitHub.
Never hardcode Moodle tokens or AI API keys in Python files.
Use AI_PROVIDER=gemini to use Gemini.
Use AI_PROVIDER=ollama to use local Ollama.
MOODLE_BASE_URL should not include /webservice/rest/server.php.
```

Correct:

```env
MOODLE_BASE_URL=https://moodle.skillsynch.org
```

Incorrect:

```env
MOODLE_BASE_URL=https://moodle.skillsynch.org/webservice/rest/server.php
```

---

# 5. Moodle Setup Requirements

## 5.1 External Service

You created one Moodle External Service:

```text
SkillSync Read Service
```

This is the correct approach. The categories below are not separate Moodle services. They are different groups of functions added to the same service.

## 5.2 Required Moodle Web Service Functions

Currently added and working:

```text
core_webservice_get_site_info
core_user_get_users_by_field
core_enrol_get_users_courses
core_enrol_get_enrolled_users
core_course_get_contents
core_course_get_courses_by_field
core_course_get_course_module_by_instance
mod_assign_get_assignments
mod_assign_get_submission_status
mod_assign_get_grades
core_grading_get_definitions
core_grading_get_gradingform_instances
mod_quiz_get_quizzes_by_courses
mod_quiz_get_user_quiz_attempts
mod_quiz_get_user_best_grade
core_competency_list_course_competencies
core_competency_list_course_module_competencies
```

Optional future functions for question-level quiz evidence:

```text
mod_quiz_get_attempt_review
core_competency_read_competency
```

## 5.3 Moodle API User

You created a dedicated API user:

```text
skillsync_api
```

This user should:

```text
Be authorised for SkillSync Read Service
Have a token for SkillSync Read Service
Be enrolled in relevant courses as Manager or Teacher
Have permission to view assignments, grades, feedback, and rubrics
```

Important finding:

```text
System-level Manager alone was not enough for mod_assign_get_assignments.
The skillsync_api user also needed to be enrolled directly into IT101 as Manager.
```

For future courses, either:

```text
Enrol skillsync_api into each course as Manager/Teacher
```

or configure a course-category/system role that Moodle actually recognises for the required assignment APIs.

---

# 6. Current Moodle Test Subject Structure

Current test course:

```text
Course: Introduction to IT
Shortname: IT101
Course ID: 2
```

Current structure:

```text
General
├── Announcements
├── Welcome to IT101
└── Course Learning Outcomes / SILOs

Assignments
└── Assignment 1: Report

Quiz
├── Quiz 1
└── Quiz 2
```

Current known assignment:

```text
Assignment name: Assignment 1: Report
Assignment ID / assignid: 1
Course module ID / cmid: 4
Max grade: 100
Submission type: PDF/file submission
Rubric: configured
Feedback comments: enabled
Edit PDF feedback: enabled
```

Current known test student:

```text
Student name: Susan
Moodle user ID: 9
Assignment 1 submitted: Yes
Assignment 1 graded: Yes
Assignment grade: 70 / 100
Quiz 1 completed: Yes
Quiz 2 completed: Yes
```

---

# 7. AI Layer Documentation

## 7.1 `ai/schemas.py`

This file defines the required AI output structure using Pydantic.

The main model is:

```python
AIFeedback
```

Current AI output fields:

```text
summary
areas_for_improvement
evidence_based_study_plan
generated_quiz_questions
```

### Current AI Output Structure

```json
{
  "summary": "Student-friendly summary of progress.",
  "areas_for_improvement": [
    {
      "title": "Weak area title",
      "details": "Brief explanation of the weak area."
    }
  ],
  "evidence_based_study_plan": [
    {
      "weak_area": "Specific weak area",
      "evidence": "Evidence from Moodle/rubric/feedback",
      "learning_goal": "Target learning outcome",
      "priority": "high",
      "study_steps": [
        {
          "step_number": 1,
          "task": "Study task",
          "method": "How to complete it",
          "rationale": "Why this helps",
          "estimated_time_minutes": 45
        }
      ],
      "success_measure": "How the student knows they improved"
    }
  ],
  "generated_quiz_questions": [
    {
      "weak_area": "Weak topic",
      "questions": [
        {
          "question": "MCQ question",
          "choice_1": "Answer option",
          "choice_2": "Answer option",
          "choice_3": "Answer option",
          "correct_answer": "Correct answer",
          "explanation": "Why the answer is correct"
        }
      ]
    }
  ]
}
```

Edit `schemas.py` when:

```text
You want to add or remove output fields.
You want to change the structure of the AI response.
You want the frontend/database to receive different JSON fields.
```

---

## 7.2 `ai/prompts.py`

This file controls the AI’s behaviour.

It tells the model:

```text
What role it has
What data it is analysing
What tone to use
How detailed to be
What output format to follow
What not to invent
```

Edit `prompts.py` when:

```text
The AI response is too short
The AI response is too generic
The AI is not following the desired tone
The AI needs more explicit instructions
You want stronger study plans or different MCQ style
```

Simple rule:

```text
schemas.py = what fields the AI must return
prompts.py = how the AI should write and reason
```

---

## 7.3 `ai/provider_factory.py`

This file selects the correct AI provider based on `.env`.

Example:

```env
AI_PROVIDER=gemini
```

uses:

```python
GeminiProvider
```

Example:

```env
AI_PROVIDER=ollama
```

uses:

```python
OllamaProvider
```

This means the rest of your code can call:

```python
ai_provider = get_ai_provider()
```

without caring which model is currently active.

---

## 7.4 `ai/gemini_provider.py`

This file connects to the Gemini API.

It uses:

```text
GEMINI_API_KEY
GEMINI_MODEL
GEMINI_MAX_OUTPUT_TOKENS
GEMINI_THINKING_BUDGET
```

The Gemini provider sends the AI input to Gemini and validates the response against `AIFeedback`.

Known issue:

```text
Gemini can occasionally return 503 UNAVAILABLE due to high demand.
```

When this happens, the Moodle and normaliser code are not broken. It means Gemini is temporarily overloaded.

Recommended future improvement:

```text
Add retry logic with exponential backoff.
```

---

## 7.5 `ai/ollama_provider.py`

This file connects to local Ollama.

Current model:

```text
qwen3.5:9b
```

Important Ollama options:

```python
"temperature": 0.2
"num_predict": 1800
```

Meaning:

```text
temperature controls randomness.
num_predict controls maximum output length.
```

If Ollama cuts off JSON output, increase:

```python
"num_predict": 2500
```

If Ollama times out, increase:

```env
OLLAMA_TIMEOUT_SECONDS=900
```

---

# 8. Mastery Model Documentation

## 8.1 Purpose

The Mastery Model calculates how well a student understands a subject based on SILOs.

The key rule is:

```text
The Mastery Model calculates scores.
The AI explains the scores.
```

The AI should not invent mastery values.

---

## 8.2 `mastery/mastery_model.py`

This file contains the core mastery logic.

Main data classes:

```text
SILO
Assessment
AssessmentSiloMapping
StudentResult
SiloEvidence
SiloMastery
MasteryReport
```

### `SILO`

Represents a Subject Intended Learning Outcome.

Example:

```python
SILO(
    silo_id="IT101-SILO-1",
    course_id="2",
    title="Explanation of IT concepts",
    description="Explain foundational IT concepts."
)
```

### `Assessment`

Represents an assessment or evidence item.

Example:

```python
Assessment(
    assessment_id="1-criterion-5",
    course_id="2",
    name="Assignment 1: Report - Explanation of IT concepts",
    weight_percent=25
)
```

### `AssessmentSiloMapping`

Maps an assessment/evidence item to a SILO.

Example:

```python
AssessmentSiloMapping(
    assessment_id="1-criterion-5",
    silo_id="IT101-SILO-1",
    coverage_weight=1.0
)
```

### `StudentResult`

Stores a student score for an assessment/evidence item.

Example:

```python
StudentResult(
    student_id="9",
    assessment_id="1-criterion-5",
    score_percent=40.0
)
```

---

## 8.3 Mastery Formula

For each SILO:

```text
SILO mastery =
sum(student_score × assessment_weight × SILO_coverage)
÷
sum(assessment_weight × SILO_coverage)
```

For rubric-based assignment evidence, each rubric criterion becomes a pseudo-assessment.

Example:

```text
Assignment 1 criterion: Explanation of IT concepts
Related SILO: IT101-SILO-1
Rubric score: 10 / 25
Score percent: 40%
```

This becomes:

```text
SILO 1 mastery = 40%
```

---

## 8.4 Confidence Levels

The Mastery Model also calculates confidence:

```text
none
low
medium
high
```

Confidence depends on:

```text
number of evidence items
total evidence weight
```

A mastery score based on several assessments should be treated as more reliable than a score based on one small quiz.

---

## 8.5 `mastery/mock_data.py`

This contains older mock data used before Moodle integration worked.

It is still useful for isolated Mastery Model testing, but the main project is now moving toward real Moodle-derived evidence.

Use mock data when:

```text
Moodle is offline
You want to test mastery logic without API calls
You need quick predictable test data
```

---

# 9. Moodle API Layer

## 9.1 `moodle/client.py`

This is the generic Moodle REST client.

It calls Moodle’s single REST endpoint:

```text
/webservice/rest/server.php
```

Every function call includes:

```text
wstoken
wsfunction
moodlewsrestformat
```

Example internal call:

```python
client.call(
    "core_webservice_get_site_info"
)
```

Example with parameters:

```python
client.call(
    "core_user_get_users_by_field",
    {
        "field": "email",
        "values[0]": "student@example.com"
    }
)
```

The client also checks for Moodle API errors:

```python
if isinstance(data, dict) and "exception" in data:
    raise RuntimeError(...)
```

This is important because Moodle often returns API errors as JSON rather than HTTP errors.

---

# 10. Moodle Services

Services are small wrappers around Moodle API functions.

They keep raw API calls out of the main scripts.

---

## 10.1 `moodle/services/users.py`

Purpose:

```text
Look up Moodle users
Get enrolled courses for a user
```

Important functions:

```python
get_user_by_field(client, field, value)
get_user_courses(client, user_id)
```

Example usage:

```python
student = get_user_by_field(
    client=client,
    field="username",
    value="susan"
)
```

Supported fields include:

```text
email
username
idnumber
id
```

---

## 10.2 `moodle/services/courses.py`

Purpose:

```text
Retrieve course details and course contents
Summarise modules inside a course
Filter assessment modules
```

Important functions:

```python
get_course_contents(client, course_id)
get_course_by_id(client, course_id)
summarise_course_modules(course_contents)
filter_assessment_modules(module_summary)
```

This helped identify:

```text
Assignment 1: Report
cmid = 4
instance / assignment_id = 1
```

---

## 10.3 `moodle/services/assignments.py`

Purpose:

```text
Retrieve assignments
Retrieve student submission status
Retrieve assignment grades
Find student-specific grade
Find assignment cmid automatically
```

Important functions:

```python
get_assignments_by_course(client, course_id)
summarise_assignments(assignments_response)
get_assignment_submission_status(client, assignment_id, user_id)
get_assignment_grades(client, assignment_id)
find_student_grade(grades_response, user_id)
find_assignment_by_id(assignments_response, assignment_id)
get_assignment_cmid(client, course_id, assignment_id)
```

Important distinction:

```text
assignment_id / assignid = used for submissions and grades
cmid / course_module_id = used for rubric and module-level data
```

For Assignment 1:

```text
assignment_id = 1
cmid = 4
```

In production, you should not manually pass `cmid`. The code should discover it using `get_assignment_cmid()`.

---

## 10.4 `moodle/services/rubrics.py`

Purpose:

```text
Retrieve rubric/advanced grading definitions
Retrieve completed rubric instances/fillings
Match a rubric instance to a student grade
```

Important functions:

```python
get_grading_definitions(client, course_module_id, area_name="submissions")
get_gradingform_instances(client, definition_id)
extract_definition_ids(definitions_response)
summarise_grading_definitions(definitions_response)
summarise_grading_instances(instances_response)
find_rubric_instance_for_grade(instances_response, grade_id)
```

Important finding:

```text
Moodle links completed rubric instances to grade records using itemid.
```

For Susan:

```text
student grade id = 4
rubric instance item_id = 4
```

So the correct completed rubric is found by:

```python
rubric_instance["itemid"] == student_grade["id"]
```

---

## 10.5 `moodle/services/quizzes.py`

Purpose:

```text
Retrieve Moodle quiz activities
Find a quiz by Moodle quiz ID
Retrieve a student's quiz attempts
Retrieve the student's best/final quiz grade
Find a quiz course module ID / cmid
```

Important functions:

```python
get_quizzes_by_course(client, course_id)
summarise_quizzes(quizzes_response)
find_quiz_by_id(quizzes_response, quiz_id)
get_user_quiz_attempts(client, quiz_id, user_id, status="all")
get_user_best_grade(client, quiz_id, user_id)
get_quiz_cmid(client, course_id, quiz_id)
```

Important Moodle 5.x note:

```text
Use mod_quiz_get_user_quiz_attempts.
Do not use the older/deprecated mod_quiz_get_user_attempts name.
```

For the IT101 test course:

```text
Quiz 1
quiz_id = 1
cmid = 6

Quiz 2
quiz_id = 2
cmid = 8
```

---

# 11. Moodle Normalisers

Normalisers convert Moodle’s raw responses into cleaner project-specific structures.

This is important because Moodle responses are large, nested, and inconsistent.

---

## 11.1 `moodle/normalisers/assignment_normaliser.py`

Purpose:

```text
Build one clean assignment context object for a student and assignment.
```

Main function:

```python
build_student_assignment_context(
    client,
    student_user_id,
    course_id,
    assignment_id
)
```

This function combines:

```text
assignment details
submission status
submitted files
grade
feedback comments
feedback files
rubric fillings
```

### Output Shape

```json
{
  "student_user_id": 9,
  "course_id": 2,
  "assignment_id": 1,
  "course_module_id": 4,
  "assignment_name": "Assignment 1: Report",
  "assignment_max_grade": 100.0,
  "assignment_task": "You need to complete a 500 word report...",
  "submission": {
    "submission_id": 5,
    "attempt_number": 2,
    "status": "submitted",
    "submitted_files": []
  },
  "grading": {
    "is_graded": true,
    "grading_status": "graded",
    "grade_id": 4,
    "grade_percent": 70.0,
    "grade_display": "70.00 / 100.00"
  },
  "feedback": {
    "comment": "Teacher feedback text",
    "feedback_files": []
  },
  "rubric": {
    "rubric_fillings": []
  }
}
```

### Helper Functions

```python
clean_html_text(value)
parse_moodle_grade(value)
extract_submission_files(submission_status)
extract_feedback_comment(submission_status)
extract_feedback_files(submission_status)
extract_assignment_task(submission_status, assignment)
normalise_rubric_instance(rubric_instance)
get_student_rubric_fillings(client, course_module_id, grade_id)
```

### Important Notes

`clean_html_text()` removes Moodle HTML tags and converts fields into readable text.

`parse_moodle_grade()` converts grades like:

```text
"70.00000"
```

to:

```python
70.0
```

It also treats Moodle’s ungraded value:

```text
-1.00000
```

as:

```python
None
```

---

## 11.2 `moodle/normalisers/ai_input_builder.py`

Purpose:

```text
Convert normalised Moodle assignment context into AI-ready input.
```

Main function:

```python
build_assignment_ai_input(
    assignment_context,
    student_name=None,
    course_name=None,
    criterion_mapping=None
)
```

This removes unnecessary Moodle metadata and keeps only learning-relevant evidence.

### AI Input Shape

```json
{
  "source": "moodle",
  "data_type": "assignment_learning_evidence",
  "student": {
    "moodle_user_id": 9,
    "name": "Susan"
  },
  "course": {
    "course_id": 2,
    "course_name": "Introduction to IT"
  },
  "assessment": {
    "assessment_type": "assignment",
    "assignment_id": 1,
    "course_module_id": 4,
    "name": "Assignment 1: Report",
    "max_grade": 100.0,
    "task": "Assignment task text"
  },
  "submission": {
    "status": "submitted",
    "submitted_files": []
  },
  "performance": {
    "is_graded": true,
    "grade_percent": 70.0,
    "grade_display": "70.00 / 100.00"
  },
  "teacher_feedback": {
    "comment": "Teacher feedback",
    "feedback_files": []
  },
  "rubric_evidence": [],
  "weak_topics": [],
  "ai_guidance": {}
}
```

### Weak Topic Detection

Weak topics are inferred from:

```text
overall assignment grade
rubric score percentages
teacher feedback keywords
```

Current weak threshold:

```text
70%
```

If a rubric criterion score is below 70%, it is considered a weak topic.

Example from Susan:

```text
IT101-SILO-1: 40%
IT101-SILO-2: 60%
IT101-SILO-3: 80%
IT101-SILO-4: 100%
```

Weak topics:

```text
Explanation of IT concepts
Role of IT in organisations
Teacher feedback
```

### Moodle-Backed Rubric Mapping

The temporary `IT101_RUBRIC_CRITERION_MAPPING` has been replaced by
`moodle/evidence_mapper.py`.

The mapper now:

```text
uses Moodle activity competency links
uses Moodle rubric definitions and level scores
supports explicit criterion_id -> competency_id mappings
falls back to SILO code matching for IT101 development/testing
logs warnings instead of silently guessing when a mapping cannot be resolved
```

The long-term production source for explicit mappings should be the backend
database. The JSON mapping-file option in the test scripts is a lightweight
stand-in for that database table during local testing.

---

## 11.3 `moodle/normalisers/mastery_input_builder.py`

Purpose:

```text
Convert Moodle assignment AI input into Mastery Model input objects.
```

Main function:

```python
build_mastery_inputs_from_assignment_ai_input(
    ai_input,
    assignment_weight_percent=100.0
)

build_mastery_inputs_from_quiz_contexts(
    quiz_contexts,
    quiz_weight_percent_by_id=None
)

merge_mastery_input_bundles(
    student_id,
    course_id,
    bundles
)
```

These functions convert:

```text
assignment rubric evidence
quiz grade evidence
```

into:

```text
SILO
Assessment
AssessmentSiloMapping
StudentResult
```

### Why This Exists

The Mastery Model expects structured objects, not raw Moodle JSON.

This builder bridges:

```text
Moodle-derived AI input
→ Mastery Model objects
```

### Output

Returns a `MasteryInputBundle`:

```python
MasteryInputBundle(
    student_id="9",
    course_id="2",
    silos=[...],
    assessments=[...],
    mappings=[...],
    student_results=[...]
)
```

### How It Works

Each rubric criterion becomes a pseudo-assessment.
Each valid completed quiz becomes one assessment evidence item.

Example:

```text
Assignment 1: Report - Explanation of IT concepts
Score: 40%
Maps to: IT101-SILO-1

Quiz 1
Score: 100%
Maps to: IT101-SILO1 and IT101-SILO4
```

This allows the existing Mastery Model formula to work without rewriting the model.

---

## 11.4 `moodle/normalisers/quiz_normaliser.py`

Purpose:

```text
Convert Moodle quiz API responses into clean mastery-ready quiz evidence.
```

Main functions:

```python
normalise_student_quiz_context(...)
build_student_quiz_context(...)
build_student_course_quiz_contexts(...)
build_quiz_competency_mappings(...)
```

The normaliser uses:

```text
mod_quiz_get_user_quiz_attempts
mod_quiz_get_user_best_grade
core_competency_list_course_module_competencies
```

Only completed attempts can become mastery evidence:

```text
finished
submitted
```

Skipped quiz evidence records include reasons such as:

```text
no_completed_attempt
missing_best_grade
missing_competency_mapping
```

Each valid quiz context contains:

```text
quiz_id
course_module_id
quiz_name
best_grade.grade_percent
selected_attempt
competency_mappings
is_valid_for_mastery
skip_reasons
```

Mapping rule:

```text
Explicit quiz mappings win.
If no explicit mapping exists, Moodle activity-level competencies are used.
If a quiz maps to several competencies, coverage is split evenly unless explicit weights are supplied.
```

---

# 12. Service Wrappers

## `services/assignment_feedback_service.py`

Purpose:

```text
Provide one clean function that runs the full assignment feedback workflow.
```

Main function:

```python
generate_assignment_feedback_for_student(
    student_user_id,
    course_id,
    assignment_id,
    student_name=None,
    course_name=None
)
```

This function:

```text
1. Loads settings from .env
2. Creates MoodleClient
3. Builds normalised assignment context
4. Builds AI input
5. Selects Gemini or Ollama provider
6. Generates AI feedback
7. Returns assignment_context, ai_input, and ai_feedback
```

### Return Structure

```python
{
    "assignment_context": assignment_context,
    "ai_input": ai_input,
    "ai_feedback": feedback.model_dump()
}
```

This function is still useful for assignment-specific feedback tests.

Example:

```python
from services.assignment_feedback_service import generate_assignment_feedback_for_student

result = generate_assignment_feedback_for_student(
    student_user_id=9,
    course_id=2,
    assignment_id=1,
    student_name="Susan",
    course_name="Introduction to IT",
)

feedback = result["ai_feedback"]
```

---

## `services/learning_report_service.py`

Purpose:

```text
Generate full learning reports and course-level learning profiles.
Calculate mastery before calling the AI provider.
```

Assignment-level function:

```python
generate_learning_report_for_assignment(
    student_user_id=9,
    course_id=2,
    assignment_id=1,
    student_name="Susan",
    course_name="Introduction to IT",
    assignment_weight_percent=100,
)
```

Course-level function:

```python
generate_student_learning_profile(
    student_user_id=9,
    course_id=2,
    student_name="Susan",
    course_name="Introduction to IT",
    assignment_ids=None,
    quiz_ids=None,
    assessment_weights=None,
    explicit_assignment_mappings=None,
    explicit_quiz_mappings=None,
)
```

The course-level profile combines:

```text
assignment rubric evidence
quiz grade evidence
calculated mastery report
calculated weak areas
AI summary, study plan, generated MCQs, and recommendations
```

The stable course-level report key is:

```text
moodle:course:{course_id}:student:{student_user_id}
```

Example:

```text
moodle:course:2:student:9
```

---

## `services/report_orchestration_service.py`

Purpose:

```text
Backend-facing get-or-generate workflow with Supabase persistence and job tracking.
```

Recommended backend entry point for the course dashboard:

```python
from services.report_orchestration_service import get_or_generate_student_learning_profile

response = get_or_generate_student_learning_profile(
    student_user_id=9,
    course_id=2,
    student_name="Susan",
    course_name="Introduction to IT",
    force_refresh=False,
)
```

The older assignment-specific orchestration function still exists:

```python
get_or_generate_learning_report(...)
```

Use it when the backend/frontend wants an Assignment 1 drill-down report.

Report scopes:

```text
assignment_learning_report
  One report for one assignment.
  Key example: moodle:course:2:assignment:1:student:9

course_learning_profile
  Main course-level mastery profile.
  Key example: moodle:course:2:student:9
```

It is valid for Susan to have both report types because they answer different questions.

---

## FastAPI Backend API

The project includes a thin FastAPI backend for the frontend to call.

Entrypoint:

```text
api/main.py
```

Required packages are already listed in `requirements.txt`:

```text
fastapi
uvicorn[standard]
```

Start the API from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --host 127.0.0.1 --port 3000
```

Local API URLs:

```text
Swagger docs:  http://127.0.0.1:3000/docs
OpenAPI JSON:  http://127.0.0.1:3000/openapi.json
Health check:  http://127.0.0.1:3000/health
```

Hosted API URL:

```text
https://api.skillsynch.org
```

The Cloudflare tunnel routes the public API hostname to the local backend at:

```text
http://localhost:3000/
```

Do not document, commit, or share the Cloudflare tunnel token. `cloudflared`
can run as a Windows service, but FastAPI still needs to be running locally
unless the API is separately service-managed.

Frontend environment values:

```text
VITE_SKILLSYNC_API_BASE_URL=https://api.skillsynch.org
```

Local frontend fallback:

```text
VITE_SKILLSYNC_API_BASE_URL=http://127.0.0.1:3000
```

Frontend requests must send the logged-in student's Supabase session token:

```http
Authorization: Bearer <supabase-access-token>
```

Never expose server-only secrets in frontend code or frontend `.env` files:

```text
SUPABASE_SERVICE_ROLE_KEY
MOODLE_TOKEN
GEMINI_API_KEY
```

Existing FastAPI endpoints:

```http
GET /health
GET /health?check_moodle=true
GET /api/me/courses
GET /api/me/profile?course_id=<course_id>
POST /api/me/profile/refresh
GET /api/jobs/{job_id}
```

`GET /health` returns backend configuration status. Add
`check_moodle=true` when you also want to test whether Moodle is reachable.

`GET /api/me/courses` returns the authenticated student's Moodle course
enrolments and any existing course-profile summary. It does not generate
missing or stale reports.

`GET /api/me/profile?course_id=<course_id>` returns a fresh stored
course-level profile when available, or generates one when missing or stale.
The API verifies that the authenticated student is enrolled in the selected
course.

Important response fields:

```text
status
source
job_id
learning_report_id
student_id
report_key
overall_mastery_score
generated_at
report
```

`POST /api/me/profile/refresh` forces a Moodle, mastery, AI, and Supabase
regeneration for the selected course. The request body can include optional
course name, assignment IDs, quiz IDs, assessment weights, and explicit
assessment mappings.

Example refresh body:

```json
{
  "course_id": 2,
  "course_name": "Introduction to IT",
  "assignment_ids": null,
  "quiz_ids": null,
  "assessment_weights": null,
  "explicit_assignment_mappings": null,
  "explicit_quiz_mappings": null
}
```

`GET /api/jobs/{job_id}` returns report generation job status for jobs owned by
the authenticated student.

---

# 13. Test Scripts

All scripts should be run from the project root using:

```powershell
python -m scripts.script_name
```

Do not run scripts directly from inside the `scripts/` folder, because imports may fail.

---

## 13.1 Test Moodle Connection

Command:

```powershell
python -m scripts.test_moodle_connection
```

Purpose:

```text
Tests Moodle token, base URL, REST protocol, and external service access.
```

Expected output:

```text
Moodle site info
username
userid
available functions
```

Use this first if anything Moodle-related breaks.

---

## 13.2 Inspect Moodle User and Courses

Command by username:

```powershell
python -m scripts.inspect_moodle_users_courses --username susan
```

Command by user ID:

```powershell
python -m scripts.inspect_moodle_users_courses --userid 9
```

Command by email:

```powershell
python -m scripts.inspect_moodle_users_courses --email susan@example.com
```

Purpose:

```text
Finds a Moodle user and lists their enrolled courses.
```

Useful for:

```text
Confirming student user ID
Confirming course ID
Checking enrolments
```

---

## 13.3 Inspect Course Assignments

Command:

```powershell
python -m scripts.inspect_moodle_course_assignments --courseid 2
```

With raw Moodle response:

```powershell
python -m scripts.inspect_moodle_course_assignments --courseid 2 --raw
```

Purpose:

```text
Retrieves course details, course contents, assignment modules, and assignment data.
```

Useful for finding:

```text
assignment_id
cmid
assignment name
assignment task
assignment grade config
```

Known IT101 values:

```text
course_id = 2
assignment_id = 1
cmid = 4
```

---

## 13.4 Inspect Assignment Submission

Command:

```powershell
python -m scripts.inspect_assignment_submission --userid 9 --assignmentid 1
```

Purpose:

```text
Retrieves raw student submission status, grade, files, and feedback.
```

Useful for checking:

```text
submitted file URL
grade
feedback comments
grading status
previous attempts
```

---

## 13.5 Inspect Assignment Rubric

Command:

```powershell
python -m scripts.inspect_assignment_rubric --cmid 4
```

With raw output:

```powershell
python -m scripts.inspect_assignment_rubric --cmid 4 --raw
```

Purpose:

```text
Retrieves rubric definitions and grading form instances.
```

Note:

```text
Passing cmid manually is only for testing.
Production code discovers cmid automatically.
```

---

## 13.6 Test Assignment Normaliser

Command:

```powershell
python -m scripts.test_assignment_normaliser --userid 9 --courseid 2 --assignmentid 1
```

Purpose:

```text
Builds one clean normalised assignment context object.
```

Expected output includes:

```text
assignment task
submission status
submitted files
grade
feedback comment
rubric fillings
```

---

## 13.7 Test Assignment AI Input Builder

Command:

```powershell
python -m scripts.test_assignment_ai_input --userid 9 --courseid 2 --assignmentid 1 --studentname Susan --coursename "Introduction to IT"
```

Send to AI:

```powershell
python -m scripts.test_assignment_ai_input --userid 9 --courseid 2 --assignmentid 1 --studentname Susan --coursename "Introduction to IT" --send-to-ai
```

Purpose:

```text
Builds AI-ready input from Moodle assignment context.
Optionally sends it to Gemini/Ollama.
```

Use this when debugging:

```text
AI input structure
weak topic detection
rubric evidence enrichment
```

---

## 13.8 Test Assignment Feedback Service Wrapper

Command:

```powershell
python -m scripts.test_assignment_feedback_service --userid 9 --courseid 2 --assignmentid 1 --studentname Susan --coursename "Introduction to IT"
```

Purpose:

```text
Tests the complete assignment feedback workflow through one wrapper function.
```

This is the most important end-to-end test for assignment feedback.

Expected output:

```text
Assignment Context
AI Input
AI Feedback
```

---

## 13.9 Test Mastery From Assignment AI Input

Command:

```powershell
python -m scripts.test_mastery_from_assignment_ai_input --userid 9 --courseid 2 --assignmentid 1 --studentname Susan --coursename "Introduction to IT"
```

With assignment weight:

```powershell
python -m scripts.test_mastery_from_assignment_ai_input --userid 9 --courseid 2 --assignmentid 1 --studentname Susan --coursename "Introduction to IT" --assignment-weight 40
```

Purpose:

```text
Converts Moodle rubric evidence into Mastery Model inputs and calculates SILO mastery.
```

Expected Susan result based on current rubric:

```text
IT101-SILO-1: 40%
IT101-SILO-2: 60%
IT101-SILO-3: 80%
IT101-SILO-4: 100%
Overall: approximately 70%
```

---

## 13.10 Test Quiz Normaliser

Command:

```powershell
python -m scripts.test_quiz_normaliser
```

Purpose:

```text
Tests quiz attempt state handling, missing grade handling, explicit quiz mappings,
and quiz context validation without calling live Moodle.
```

Expected output:

```text
Quiz normaliser tests passed.
```

---

## 13.11 Test Course Profile Mastery Inputs

Command:

```powershell
python -m scripts.test_course_profile_mastery_inputs
```

Purpose:

```text
Tests merging assignment rubric evidence and quiz grade evidence into one MasteryInputBundle.
```

Expected output:

```text
Course profile mastery input tests passed.
```

---

## 13.12 Generate Student Learning Profile

Local generation command:

```powershell
python -m scripts.generate_student_learning_profile --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT"
```

Save to Supabase:

```powershell
python -m scripts.generate_student_learning_profile --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT" --save-to-supabase
```

Purpose:

```text
Runs the course-level Moodle -> mastery -> AI workflow directly.
```

Useful optional arguments:

```text
--assignmentids 1
--quizids 1,2
--weights-file weights.json
--assignment-mapping-file assignment_mappings.json
--quiz-mapping-file quiz_mappings.json
--output profile.json
```

---

## 13.13 Simulate Backend Course Profile Request

Command:

```powershell
python -m scripts.simulate_backend_profile_request --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT"
```

Force live regeneration:

```powershell
python -m scripts.simulate_backend_profile_request --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT" --force-refresh
```

Purpose:

```text
Tests the backend-facing get-or-generate course profile orchestration.
This creates/updates a report_generation_jobs row and saves the profile to Supabase.
```

---

## 13.14 Inspect Course Profile Job Status

Command:

```powershell
python -m scripts.inspect_report_generation_job --userid 9 --courseid 2 --course-profile
```

Purpose:

```text
Looks up the latest report_generation_jobs row for the course-level profile key.
```

---

# 14. Current Working Pipeline

## Assignment Feedback Pipeline

```text
Input:
student_user_id = 9
course_id = 2
assignment_id = 1

Flow:
services/assignment_feedback_service.py
  ↓
build_student_assignment_context()
  ↓
build_assignment_ai_input()
  ↓
get_ai_provider()
  ↓
Gemini/Ollama
  ↓
AIFeedback JSON
```

Output:

```text
summary
areas_for_improvement
evidence_based_study_plan
generated_quiz_questions
```

---

## Course-Level Mastery Pipeline

```text
Input:
student_user_id = 9
course_id = 2

Flow:
generate_student_learning_profile()
  |
build_student_assignment_context()
  |
build_student_course_quiz_contexts()
  |
build_mastery_inputs_from_assignment_ai_input()
  |
build_mastery_inputs_from_quiz_contexts()
  |
merge_mastery_input_bundles()
  ↓
calculate_mastery_report()
  ↓
AI provider explains calculated mastery
  |
Supabase save
```

Output:

```text
overall_mastery_score
silo_mastery
weakest_silos
assignment_evidence
quiz_evidence
evidence items
confidence levels
ai_feedback
```

Verified live result for Susan:

```text
report_key = moodle:course:2:student:9
report_type = course_learning_profile
overall_mastery_score = 76.67
included assessments = Assignment 1: Report, Quiz 1, Quiz 2
```

---

# 15. Relevant Information for Group Members

## 15.1 Backend Developer

Most relevant files:

```text
services/report_orchestration_service.py
services/learning_report_service.py
services/assignment_feedback_service.py
moodle/normalisers/assignment_normaliser.py
moodle/normalisers/quiz_normaliser.py
moodle/normalisers/mastery_input_builder.py
mastery/mastery_model.py
ai/schemas.py
```

Most important function:

```python
get_or_generate_student_learning_profile(...)
```

Backend can call:

```python
result = get_or_generate_student_learning_profile(
    student_user_id=9,
    course_id=2,
    student_name="Susan",
    course_name="Introduction to IT",
    force_refresh=False,
)
```

Backend receives:

```python
result["status"]
result["report_key"]
result["overall_mastery_score"]
result["report"]
```

### Database Storage Recommendation

Backend can store or read:

```text
learning_reports.full_report
learning_reports.mastery_report
learning_reports.ai_feedback
student_evidence rows
competency_mastery rows
```

For relational tables, suggested entities:

```text
students
learning_reports
student_evidence
competency_mastery
ai_quiz_question_groups
ai_quiz_questions
ai_recommendations
report_generation_jobs
```

Minimum storage for MVP:

```text
students
learning_reports
competency_mastery
student_evidence
report_generation_jobs
```

---

## 15.2 Moodle Developer / Moodle Admin

Most relevant setup:

```text
SkillSync Read Service
skillsync_api user
Course enrolment/permissions
Assignment configuration
Rubric configuration
SILO/competency configuration
Quiz setup
```

Each course should ideally have:

```text
Clear SILOs / competencies
Assignments with grading rubrics
Rubric criteria mapped to SILOs
File submissions enabled
Feedback comments enabled
Grades visible
Quizzes configured and linked to competencies for quiz mastery evidence
```

For assignment-based mastery, each rubric criterion should clearly relate to a SILO.

For quiz-based mastery, each quiz activity should have Moodle activity-level
competencies linked. If Moodle competencies are missing, the backend can pass
explicit quiz mappings.

Example:

```text
Criterion: Explanation of IT concepts
SILO: IT101-SILO-1
Max score: 25
```

---

## 15.3 Frontend Developer

Relevant output:

```text
ai_feedback
mastery_report
calculated_weak_areas
included_assessments
assignment_evidence
quiz_evidence
student_evidence
```

Frontend can display:

```text
summary
areas_for_improvement
evidence_based_study_plan
generated_quiz_questions
overall_mastery_score
per-SILO mastery scores
submitted assignment info
teacher feedback
quiz evidence and quiz scores
```

Recommended UI sections:

```text
Student Overview
Mastery Score
Weak Areas
Evidence-Based Study Plan
Practice Questions
Assignment Evidence
Quiz Evidence
Teacher Feedback
```

Important frontend rule:

```text
For the main student dashboard, use report_type = course_learning_profile.
Assignment reports can be shown as assessment-specific drill-downs.
Do not display assignment_learning_report and course_learning_profile as duplicate student summaries.
```

---

## 15.4 AI Developer / You

Relevant files:

```text
ai/prompts.py
ai/schemas.py
ai/gemini_provider.py
ai/ollama_provider.py
moodle/normalisers/ai_input_builder.py
moodle/normalisers/quiz_normaliser.py
services/learning_report_service.py
services/report_orchestration_service.py
services/assignment_feedback_service.py
```

Edit `prompts.py` to improve:

```text
tone
level of detail
study plan quality
MCQ difficulty
student-friendly language
```

Edit `schemas.py` to change:

```text
AI output fields
JSON shape
database/frontend contract
```

---

# 16. Known Issues and Limitations

## 16.1 Feedback Typo

Current Moodle feedback for Susan appears as:

```text
t meets the basics...
```

It likely should be:

```text
It meets the basics...
```

This seems to be a typo in Moodle feedback, not a Python extraction issue.

Fix in Moodle if desired.

---

## 16.2 PDF Content Is Not Yet Read

The system currently extracts PDF metadata:

```text
filename
fileurl
mimetype
filesize
```

It does not yet download or parse the PDF text.

The AI is instructed:

```text
Do not claim to have read the submitted PDF unless extracted text is provided.
```

Future improvement:

```text
Download submitted PDF
Extract text
Add submission_text to assignment_context or ai_input
Allow AI to analyse actual student writing
```

---

## 16.3 Rubric Mapping Now Uses A Mapping Layer

Rubric mapping now lives in:

```text
moodle/evidence_mapper.py
```

The current implementation keeps the project Moodle-aware without locking the
mastery engine or LLM layer to Moodle API details. It can use explicit mappings
from a JSON file/backend table, then falls back to SILO code matching for the
IT101 test environment.

Future work:

```text
store explicit mappings in the backend database
add a frontend/admin workflow for reviewing mappings
expand evidence mapping for question-level quizzes and other activity types
```

---

## 16.4 Quiz Data Is Integrated At Quiz-Level

Susan's Quiz 1 and Quiz 2 results now feed the course-level Mastery Model.

Current quiz support:

```text
quiz-level best/final grade evidence
activity-level competency mapping
course-level mastery profile generation
Supabase storage as student_evidence.source_type = quiz_grade
```

Remaining limitation:

```text
The system does not yet use per-question quiz attempt review data.
Question-level quiz evidence would require mod_quiz_get_attempt_review and
question-to-SILO mapping.
```

---

## 17. Supabase Learning Report Storage

The AI component can now generate one final learning report object that combines:

```text
live Moodle assignment evidence
live Moodle quiz grade evidence
rubric criterion to competency mappings
calculated mastery scores
calculated weak areas
AI summary, study plan, MCQs, and recommendations
```

Assignment-level end-to-end script:

```powershell
python -m scripts.generate_learning_report --userid 9 --courseid 2 --assignmentid 1 --studentname Susan --coursename "Introduction to IT" --assignment-weight 100 --save-to-supabase
```

Course-level profile script:

```powershell
python -m scripts.generate_student_learning_profile --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT" --save-to-supabase
```

Backend-style course profile request:

```powershell
python -m scripts.simulate_backend_profile_request --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT" --force-refresh
```

Optional local JSON export for the course profile:

```powershell
python -m scripts.generate_student_learning_profile --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT" --output course_profile.json
```

The database schema is stored in:

```text
database/supabase_schema.sql
```

Apply this SQL in Supabase before using `--save-to-supabase`.

Required `.env` values:

```text
SUPABASE_URL=https://iodvvbprzbdbxlljltrq.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_backend_service_role_key
```

Important:

```text
The service role key must stay backend-only.
The frontend should not expose the service role key.
The mastery score is calculated before the LLM runs.
The LLM explains and supports the calculated result; it does not override scores.
```

### Student Association

Reports are linked to a specific student in two ways:

```text
students.id
  -> learning_reports.student_id
      -> competency_mastery.learning_report_id
      -> student_evidence.learning_report_id
      -> ai_quiz_question_groups.learning_report_id
          -> ai_quiz_questions.question_group_id
      -> ai_recommendations.learning_report_id
```

`students.moodle_user_id` stores the stable Moodle user ID, such as `9` for
Susan in the current test data. The report also keeps `student_moodle_user_id`
and `student_name` as convenient snapshot fields, but the main relational link
is `learning_reports.student_id`.

The view `student_learning_report_summary` joins students to their reports for
quick backend/frontend inspection.

Generated MCQs are stored twice on purpose:

```text
learning_reports.ai_feedback
  full AI JSON snapshot for auditing/debugging

ai_quiz_question_groups
  one row per weak area/question group

ai_quiz_questions
  one row per individual MCQ, with separate question_text, choice_1, choice_2,
  choice_3, correct_answer, and explanation columns for frontend display
```

Moodle quiz results are different from AI-generated MCQs:

```text
student_evidence.source_type = quiz_grade
  Moodle quiz performance evidence used by the mastery engine.

ai_quiz_questions
  AI-generated practice questions for study support.
```

Important report fields:

```text
learning_reports.report_type
  assignment_learning_report or course_learning_profile

learning_reports.included_assessments
  JSON list of assignment and quiz evidence sources used by a course profile.

student_evidence.quiz_moodle_id
student_evidence.quiz_attempt_id
student_evidence.course_module_id
  Quiz-specific evidence fields.
```

### Backend-Ready Report Orchestration

The recommended production-facing entry point for the main dashboard is:

```python
from services.report_orchestration_service import get_or_generate_student_learning_profile

response = get_or_generate_student_learning_profile(
    student_user_id=9,
    course_id=2,
    student_name="Susan",
    course_name="Introduction to IT",
    force_refresh=False,
)
```

This function returns one course-level profile that combines assignment rubric
evidence with Moodle quiz grade evidence. The stable report key is:

```text
moodle:course:{course_id}:student:{student_user_id}
```

The older `get_or_generate_learning_report(...)` function still exists for
assignment-specific drill-down reports. Those reports use assignment-level keys
and should not be displayed as duplicate course dashboard profiles.

Behaviour:

```text
1. Build a stable course report_key from Moodle student/course IDs.
2. Check Supabase for an existing fresh course_learning_profile.
3. If a fresh report exists and force_refresh=False, return it immediately.
4. If no fresh report exists, create a report_generation_jobs row.
5. Mark the job running.
6. Fetch Moodle assignment, rubric, and quiz evidence.
7. Normalise assignment and quiz evidence into one MasteryInputBundle.
8. Run mastery engine -> AI provider -> Supabase save.
9. Mark the job ready or failed.
10. Return a backend-friendly response.
```

Example response:

```json
{
  "status": "ready",
  "source": "generated",
  "job_id": "uuid",
  "learning_report_id": "uuid",
  "student_id": "uuid",
  "report_key": "moodle:course:2:student:9",
  "report_type": "course_learning_profile",
  "overall_mastery_score": 76.67,
  "report": {}
}
```

The job table is:

```text
report_generation_jobs
  id
  report_key
  report_type
  student_id
  student_moodle_user_id
  course_moodle_id
  assignment_moodle_id
  learning_report_id
  status: pending | running | ready | failed
  source
  force_refresh
  error_message
  started_at
  completed_at
```

For course-level profiles, `assignment_moodle_id` is null because the report
covers the whole course rather than one assignment.

Local backend simulation command:

```powershell
python -m scripts.simulate_backend_profile_request --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT"
```

Force a regeneration:

```powershell
python -m scripts.simulate_backend_profile_request --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT" --force-refresh
```

Assignment drill-down simulation command:

```powershell
python -m scripts.simulate_backend_report_request --userid 9 --courseid 2 --assignmentid 1 --studentname Susan --coursename "Introduction to IT"
```

Check a generation job by ID:

```powershell
python -m scripts.inspect_report_generation_job --jobid "job-uuid"
```

Or check the latest course profile job for a student/course:

```powershell
python -m scripts.inspect_report_generation_job --userid 9 --courseid 2 --course-profile
```

Backend polling helper:

```python
from services.report_orchestration_service import get_report_generation_status

status = get_report_generation_status(job_id="job-uuid")
```

Future work:

```text
Add question-level Moodle quiz review evidence.
Store optional explicit quiz-to-SILO mappings in the backend.
Add frontend filtering by report_type so course profiles and assignment reports are shown in the right places.
Add PDF text extraction if time allows.
Add retry/fallback handling for temporary AI provider failures.
```

---

## 16.5 Gemini Can Be Temporarily Unavailable

Gemini may return:

```text
503 UNAVAILABLE
```

This usually means the model is overloaded.

Future improvement:

```text
Add retry logic
Fallback to Ollama
Queue failed AI jobs
```

---

## 16.6 Service Account Permissions

The `skillsync_api` user must have enough access to read courses, assignments, grades, submissions, feedback, and rubrics.

If Moodle returns:

```text
User is not enrolled or does not have requested capability
```

then check:

```text
skillsync_api is enrolled in the course
skillsync_api has Manager or Teacher role
skillsync_api is authorised for SkillSync Read Service
the function is added to the external service
the token belongs to skillsync_api
```

---

# 17. Troubleshooting Guide

## Problem: `ModuleNotFoundError: No module named 'config'`

Cause:

```text
Script was run directly instead of as a module.
```

Fix:

```powershell
python -m scripts.test_moodle_connection
```

Make sure:

```text
scripts/__init__.py exists
```

---

## Problem: Moodle `Access control exception`

Likely causes:

```text
Token belongs to wrong user
User not authorised for external service
Service disabled
Token generated for wrong service
User account suspended/unconfirmed
```

Fix:

```text
Check Manage tokens
Check Authorised users
Check SkillSync Read Service enabled
Check skillsync_api account status
```

---

## Problem: `User is not enrolled or does not have requested capability`

Likely cause:

```text
API user lacks course-level permissions.
```

Fix:

```text
Enrol skillsync_api into the course as Manager or Teacher.
```

---

## Problem: Assignment Summary Empty

Cause may be:

```text
mod_assign_get_assignments permission issue
```

Fix:

```text
Run with --raw and check warnings.
Check skillsync_api enrolment.
```

---

## Problem: No Feedback Returned

Likely causes:

```text
Assignment not graded
Feedback comments not enabled
Feedback not entered
Wrong student ID
Wrong assignment ID
```

Fix:

```text
Submit as student
Grade as teacher
Enter feedback comment
Rerun inspect_assignment_submission
```

---

## Problem: Rubric Fillings Empty

Likely causes:

```text
Assignment does not use rubric
Rubric not active
Advanced grading functions not added to external service
Wrong cmid
Student not graded with rubric
```

Fix:

```text
Check assignment grading method is rubric
Add core_grading_get_definitions
Add core_grading_get_gradingform_instances
Run inspect_assignment_rubric --cmid 4
```

---

## Problem: Gemini 503 Error

Cause:

```text
Gemini service/model high demand.
```

Fix:

```text
Retry later
Switch AI_PROVIDER=ollama
Add retry logic
```

---

# 18. Recommended Next Development Steps

The project now has a course-level mastery path that combines assignment rubric
evidence and Moodle quiz grade evidence. The next development phase should focus
on making that path easier to consume in the backend/frontend and deepening quiz
evidence beyond quiz-level grades.

Recommended order:

```text
1. Keep Documentation.md aligned with the implemented course-level profile path.
2. Update backend routes to call get_or_generate_student_learning_profile(...).
3. Update frontend dashboards to use report_type = course_learning_profile for the main student summary.
4. Add explicit quiz-to-SILO mapping storage and admin/backend editing if Moodle competencies are missing.
5. Add question-level quiz attempt review evidence using mod_quiz_get_attempt_review.
6. Add frontend views for included_assessments, assignment_evidence, quiz_evidence, and student_evidence.
7. Add PDF download and text extraction if time allows.
8. Add retry/fallback handling for temporary AI provider failures.
```

---

# 19. Current Course-Level Architecture

The system now has one high-level service for the main student learning profile:

```python
generate_student_learning_profile(
    student_user_id=9,
    course_id=2
)
```

That function:

```text
Get all relevant assignments
Get all relevant quizzes
Get grades and rubric data
Calculate mastery across all SILOs
Generate AI feedback
Return one complete student learning profile
```

Possible final output:

```json
{
  "student": {},
  "course": {},
  "mastery_report": {},
  "assignment_evidence": [],
  "quiz_evidence": [],
  "ai_feedback": {}
}
```

This is the cleanest current interface for the backend and frontend. Future work
should extend this architecture with question-level quiz evidence and editable
explicit mappings, rather than creating a separate quiz report type.

---

# 20. Quick Reference: Which File Does What?

```text
config.py
Loads .env settings.

ai/schemas.py
Defines AI output JSON structure.

ai/prompts.py
Controls AI instructions and writing style.

ai/provider_factory.py
Selects Gemini or Ollama.

ai/gemini_provider.py
Calls Gemini API.

ai/ollama_provider.py
Calls local Ollama.

moodle/client.py
Generic Moodle REST API caller.

moodle/services/users.py
User lookup and course enrolment functions.

moodle/services/courses.py
Course and course content functions.

moodle/services/assignments.py
Assignment, submission, grade, and cmid functions.

moodle/services/rubrics.py
Rubric definition and completed rubric functions.

moodle/services/quizzes.py
Quiz lookup, user attempt lookup, best grade lookup, and competency lookup.

moodle/normalisers/assignment_normaliser.py
Converts raw Moodle assignment data into clean assignment_context.

moodle/normalisers/quiz_normaliser.py
Converts Moodle quiz results into clean quiz mastery evidence.

moodle/normalisers/ai_input_builder.py
Converts assignment_context into AI-ready input.

moodle/normalisers/mastery_input_builder.py
Converts assignment rubric evidence and quiz grade evidence into Mastery Model objects.

mastery/mastery_model.py
Calculates SILO mastery and overall subject mastery.

mastery/mock_data.py
Mock data for testing Mastery Model without Moodle.

services/assignment_feedback_service.py
Reusable wrapper for assignment-based AI feedback.

services/learning_report_service.py
Generates assignment learning reports and course-level student learning profiles.

services/report_orchestration_service.py
Backend-facing caching, generation job, and Supabase orchestration functions.

repositories/supabase_learning_reports.py
Persists learning reports, evidence rows, competency mastery, AI MCQs, recommendations, and jobs.

scripts/
Manual testing and inspection scripts.
```

---

# 21. Current Status Summary

The project currently supports:

```text
Moodle API authentication with skillsync_api
Student lookup
Course lookup
Assignment lookup
Submission status retrieval
Submitted PDF metadata retrieval
Grade retrieval
Feedback comment retrieval
Rubric filling retrieval
Assignment normalisation
AI input generation
Gemini/Ollama provider switching
AI-generated feedback, study plan, and MCQs
Mastery Model calculation from real Moodle rubric evidence
Moodle quiz lookup, user attempt lookup, and best grade retrieval
Quiz normalisation into mastery evidence
Course-level profile generation from assignment + quiz evidence
Supabase storage for learning_reports, student_evidence, competency_mastery, MCQs, recommendations, and jobs
Backend-style report orchestration with freshness checks and force refresh
```

The current system is no longer just mock AI output. It now uses real Moodle
assignment evidence and Moodle quiz grade evidence from IT101 and Susan's
activity to produce structured AI feedback and course-level mastery scoring.

Most important working commands:

```powershell
python -m scripts.test_moodle_connection
```

```powershell
python -m scripts.test_quiz_normaliser
```

```powershell
python -m scripts.test_course_profile_mastery_inputs
```

```powershell
python -m scripts.simulate_backend_profile_request --userid 9 --courseid 2 --studentname Susan --coursename "Introduction to IT" --force-refresh
```

Most important reusable function:

```python
get_or_generate_student_learning_profile(...)
```

Most important next feature:

```text
Add question-level Moodle quiz evidence and explicit mapping management.
```
