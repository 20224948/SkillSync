# SkillSync Backend and Frontend API Guide

The current production-style flow is:

```text
Frontend
  -> Backend API
      -> Report orchestration service
          -> Python AI component
              -> Moodle
              -> Mastery engine
              -> AI provider
              -> Supabase
      -> Backend API response
  -> Frontend renders report
```

Core rule:

```text
Python calculates mastery scores and weak areas before the LLM runs.
The AI model explains the calculated result and generates study support.
The AI model must not recalculate, invent, or override mastery scores.
```

Production MVP rule:

```text
The first student-facing page should use the course_learning_profile report.
Assignment reports remain useful detail views, but the login/dashboard flow
should start from the course profile because it combines assignment and quiz
evidence.
```

---

## 1. Current Capability

The AI component can currently:

- Fetch a student's Moodle assignment/submission/grade/feedback data.
- Fetch Moodle rubric definitions and selected rubric levels.
- Fetch Moodle assignment activity competencies.
- Map rubric criteria to competencies using explicit mappings or SILO fallback.
- Convert rubric scores into student competency evidence.
- Calculate mastery scores outside the LLM.
- Generate AI feedback, study plans, MCQs, and recommendations.
- Save the final report and child rows to Supabase.
- Track report generation status using `report_generation_jobs`.
- Generate a course-level profile from assignment rubric evidence and Moodle quiz
  grade evidence.

Current course-profile evidence sources:

```text
Assignment rubric evidence
Moodle quiz scores/results
```

---

## 2. Important IDs

Use stable external Moodle IDs when calling the hosted API.

Current IT101 test values:

```text
student Moodle user ID: 9
course Moodle ID: 2
assignment Moodle ID: 1
course module ID: 4
student name: Susan
course name: Introduction to IT
```

The course-profile API response uses this stable `report_key`:

```text
moodle:course:{course_id}:student:{student_user_id}
```

Example:

```text
moodle:course:2:student:9
```

This key is used to upsert one latest course-level learning profile for that
student/course combination.

---

## 3. Hosted FastAPI API

API hosted at:

```text
https://api.skillsynch.org
```


The API validates a Supabase Auth bearer token, resolves the user's email to a
student row or Moodle user, links `students.auth_user_id`, and then calls the
Python orchestration service. Frontend code must send the Supabase session
access token in:

```http
Authorization: Bearer <supabase-access-token>
```

### Existing FastAPI Endpoints

```http
GET /health
GET /health?check_moodle=true
GET /api/me/courses
GET /api/me/profile?course_id=2
POST /api/me/profile/refresh
GET /api/jobs/{jobId}
```

`GET /api/me/courses`:

- Returns live Moodle course enrolments for the authenticated student.
- Enriches each course with any existing `course_learning_profile` summary.
- Does not generate missing or stale reports.
- Does not accept a frontend-supplied Moodle user ID.

`GET /api/me/profile`:

- Reuses a fresh `course_learning_profile` when possible.
- Uses `freshness_minutes=1440` unless overridden.
- Regenerates synchronously when the profile is missing or stale.
- Only allows courses the authenticated student is enrolled in.
- Uses the enrolled Moodle course name when `course_name` is omitted.
- Does not accept a frontend-supplied Moodle user ID.

`POST /api/me/profile/refresh` request body:

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

`GET /api/jobs/{jobId}` only returns jobs owned by the authenticated student.

### Frontend Security Rules

The frontend should:

- Use Supabase Auth for login.
- Send the Supabase session access token to the SkillSync API.
- Never send a Moodle user ID; the API resolves it from the authenticated user.
- Never call Moodle, Gemini, Ollama, or Supabase with service-role credentials.
- Treat failed API responses as user-visible retry/error states.

Never expose these values to frontend code:

```text
MOODLE_TOKEN
GEMINI_API_KEY
SUPABASE_SERVICE_ROLE_KEY
```

---

## 4. Existing FastAPI Endpoints

### `GET /health`

Use this as a lightweight backend availability check. It returns configuration
status and can optionally check Moodle connectivity with `check_moodle=true`.

```http
GET /health
GET /health?check_moodle=true
```

### `GET /api/me/courses`

Use this after login to list the authenticated student's Moodle course
enrolments. It enriches courses with existing course-profile summaries where
available, but it does not generate missing or stale reports.

### `GET /api/me/profile?course_id=2`

Use this after the student selects a course. It returns an existing fresh
course-level profile or generates one if the profile is missing or stale. The
API verifies that the authenticated student is enrolled in the selected course.

Optional query parameters:

```text
course_name
assignment_ids
quiz_ids
freshness_minutes
```

### `POST /api/me/profile/refresh`

Use this when the student clicks refresh/retry or the UI needs to force a new
Moodle, mastery, AI, and Supabase run.

Request body:

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

### `GET /api/jobs/{jobId}`

Use this to check report generation state when a response contains a `job_id`.
The API only returns jobs owned by the authenticated student.

Possible job statuses:

```text
not_found
pending
running
ready
failed
```

---

## 5. API Response Contract

The FastAPI endpoints return this top-level shape for profile and refresh calls.

### Ready Response

```json
{
  "status": "ready",
  "source": "existing_report",
  "job_id": null,
  "learning_report_id": "uuid",
  "student_id": "uuid",
  "report_key": "moodle:course:2:student:9",
  "overall_mastery_score": 70.0,
  "generated_at": "2026-05-02T04:13:40.272991+00:00",
  "report": {}
}
```

`source` values:

```text
existing_report
generated_new_report
generation_failed
```

### Failed Response

```json
{
  "status": "failed",
  "source": "generation_failed",
  "job_id": "uuid",
  "learning_report_id": null,
  "student_id": "uuid",
  "report_key": "moodle:course:2:student:9",
  "overall_mastery_score": null,
  "generated_at": null,
  "error_message": "Readable error message",
  "report": null
}
```

### Job Status Response

```json
{
  "status": "ready",
  "job_id": "uuid",
  "report_key": "moodle:course:2:student:9",
  "student_id": "uuid",
  "student_moodle_user_id": "9",
  "course_moodle_id": "2",
  "assignment_moodle_id": "1",
  "learning_report_id": "uuid",
  "source": "generated_new_report",
  "force_refresh": true,
  "error_message": null,
  "started_at": "2026-05-02T04:13:01+00:00",
  "completed_at": "2026-05-02T04:13:40+00:00",
  "created_at": "2026-05-02T04:13:01+00:00",
  "updated_at": "2026-05-02T04:13:40+00:00"
}
```

---

## 6. Full Report Object

The `report` field contains the final AI component output.

Top-level report shape:

```json
{
  "schema_version": "1.0",
  "report_key": "moodle:course:2:student:9",
  "generated_at": "2026-05-02T04:13:40.272991+00:00",
  "student": {},
  "course": {},
  "assessment": {},
  "mastery_report": {},
  "calculated_weak_areas": [],
  "student_competency_evidence": [],
  "ai_learning_support_input": {},
  "ai_feedback": {},
  "metadata": {}
}
```

Important sections:

```text
mastery_report
  Calculated by Python. Use this for all scores.

calculated_weak_areas
  Calculated by Python. Use this for weak-area display and filtering.

student_competency_evidence
  Normalized rubric evidence used by the mastery engine.

ai_feedback
  Generated by the AI provider, grounded in the calculated evidence.

metadata
  Includes AI provider/model metadata.
```

### Mastery Report

```json
{
  "student_id": "9",
  "course_id": "2",
  "overall_mastery_score": 70.0,
  "silo_mastery": [
    {
      "silo_id": "IT101-SILO1",
      "title": "SILO 1 - Explanation of IT concepts",
      "description": "Explain foundational IT concepts.",
      "mastery_score": 40.0,
      "confidence": "medium",
      "evidence_count": 1,
      "total_evidence_weight": 100,
      "evidence": []
    }
  ],
  "weakest_silos": []
}
```

### Student Evidence

```json
{
  "student_id": "9",
  "assignment_id": "1",
  "criterion_id": "5",
  "competency_id": "123",
  "score": 10.0,
  "max_score": 25.0,
  "normalised_score": 40.0,
  "feedback": "Marker feedback for this rubric criterion",
  "mapping_source": "silo_code_fallback"
}
```

`mapping_source` values:

```text
explicit
silo_code_fallback
```

### AI Feedback

```json
{
  "summary": "Student-friendly summary.",
  "areas_for_improvement": [
    {
      "title": "Foundational IT concepts",
      "details": "Why this area needs improvement."
    }
  ],
  "evidence_based_study_plan": [
    {
      "weak_area": "Foundational IT concepts",
      "evidence": "Rubric score and teacher feedback used as evidence.",
      "learning_goal": "Improve accuracy and detail.",
      "priority": "high",
      "study_steps": [
        {
          "step_number": 1,
          "task": "Review core IT terms.",
          "method": "Make flashcards and write definitions.",
          "rationale": "Targets the weak competency.",
          "estimated_time_minutes": 30
        }
      ],
      "success_measure": "Can explain the concept clearly with examples."
    }
  ],
  "generated_quiz_questions": [
    {
      "weak_area": "Foundational IT concepts",
      "questions": [
        {
          "question": "What is cloud computing?",
          "choice_1": "A local-only storage method",
          "choice_2": "Computing services delivered over the internet",
          "choice_3": "A type of spreadsheet formula",
          "correct_answer": "Computing services delivered over the internet",
          "explanation": "Cloud computing provides services over the internet."
        }
      ]
    }
  ],
  "recommendations": [
    {
      "title": "Use workplace examples",
      "related_area": "SILO 2 - IT in Organisations",
      "reason": "The evidence shows the answer was too general.",
      "action": "Add two concrete workplace examples in revision notes."
    }
  ]
}
```

---

## 7. For Mark: Frontend Integration

### Frontend Environment

The frontend needs only browser-safe values:

```text
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<anon-or-publishable-key>
VITE_SKILLSYNC_API_BASE_URL=https://api.skillsynch.org
```

For local development against a local API:

```text
VITE_SKILLSYNC_API_BASE_URL=http://127.0.0.1:3000
```

Never put these server-only values in frontend code, `.env` files bundled into
the browser, or browser network requests:

```text
SUPABASE_SERVICE_ROLE_KEY
MOODLE_TOKEN
GEMINI_API_KEY
```

Install and create the Supabase client in the frontend:

```bash
npm install @supabase/supabase-js
```

```ts
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
);
```

### Frontend Responsibilities

The frontend should:

- Use Supabase Auth for login.
- Read report data from Supabase with the browser-safe anon/publishable key
  after RLS policies are active.
- Call the Python backend API for profile refreshes and job status.
- Display loading, ready, failed, and retry states.
- Render mastery scores from `mastery_report`, not from AI text.
- Render weak areas from `calculated_weak_areas`, not from AI guesses.
- Render AI explanations, study plans, MCQs, and recommendations.
- Never call Moodle, Gemini, Ollama, or Supabase with service-role credentials.

Primary first-page flow:

```text
1. Student logs in with Supabase Auth.
2. Frontend calls GET /api/me/courses.
3. Frontend displays the Moodle courses returned by the API.
4. Student selects a course.
5. Frontend calls GET /api/me/profile?course_id={selectedCourseId}.
6. Frontend can read existing report detail rows from Supabase for rendering.
7. If generated_at is too old, frontend calls POST /api/me/profile/refresh.
```

Mark should not send a Moodle user ID to the API. The API resolves that from the
authenticated student's email and `students.auth_user_id`.

### Supabase Authentication

For first-time students, create the Supabase Auth account from the frontend:

```ts
const { data, error } = await supabase.auth.signUp({
  email,
  password,
});

if (error) throw error;
```

If email confirmation is enabled in Supabase, `data.session` may be `null` until
the student confirms their email. In that case show a "check your email" state
and do not call the SkillSync API yet.

For returning students:

```ts
const { data, error } = await supabase.auth.signInWithPassword({
  email,
  password,
});

if (error) throw error;

const accessToken = data.session.access_token;
```

For already logged-in students after page refresh:

```ts
const { data, error } = await supabase.auth.getSession();

if (error) throw error;

const accessToken = data.session?.access_token;
```

The frontend should treat the Supabase session as the source of truth for login.
Do not ask the student to type their Moodle user ID.

### Backend API Methods

These methods talk to the local/hosted Python API, not directly to Moodle.
They require the Supabase Auth access token:

```ts
const apiHeaders = {
  Authorization: `Bearer ${accessToken}`,
  "Content-Type": "application/json",
};
```

Build URLs from `VITE_SKILLSYNC_API_BASE_URL` so the same frontend can point at
the hosted API or a local API:

```ts
const apiBaseUrl = import.meta.env.VITE_SKILLSYNC_API_BASE_URL;
```

#### GET `/health`

Use this as a basic API availability check during development or support.

```ts
const response = await fetch(`${apiBaseUrl}/health`);
const health = await response.json();

if (!response.ok) throw health;
```

#### GET `/api/me/courses`

Use this after login to list the student's current Moodle course enrolments.
This endpoint is read-only: it does not call the AI provider and does not
generate missing or stale course profiles.

```ts
const response = await fetch(
  `${apiBaseUrl}/api/me/courses`,
  {
    method: "GET",
    headers: apiHeaders,
  },
);

const coursesResponse = await response.json();

if (!response.ok) throw coursesResponse;
```

Example response:

```json
{
  "student_id": "uuid",
  "moodle_user_id": "9",
  "courses": [
    {
      "course_id": 12,
      "shortname": "IT102",
      "fullname": "Introduction to Networking",
      "display_name": "Introduction to Networking",
      "visible": true,
      "profile": {
        "status": "ready",
        "learning_report_id": "uuid",
        "report_key": "moodle:course:12:student:9",
        "overall_mastery_score": 74.5,
        "generated_at": "2026-05-03T01:20:00+00:00",
        "updated_at": "2026-05-03T01:20:00+00:00",
        "is_stale": false
      }
    }
  ]
}
```

Profile `status` values:

```text
ready
  A stored course_learning_profile exists for this student/course.

not_generated
  No stored course_learning_profile exists yet. Call GET /api/me/profile
  after the student selects the course.
```

#### GET `/api/me/profile?course_id=2`

Use this after the student selects a course. It returns the existing fresh
course profile or generates one if missing/stale. The API verifies the selected
course is one of the student's Moodle enrolments.

```ts
const response = await fetch(
  `${apiBaseUrl}/api/me/profile?course_id=${courseId}`,
  {
    method: "GET",
    headers: apiHeaders,
  },
);

const profileResponse = await response.json();

if (!response.ok) throw profileResponse;
```

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

#### POST `/api/me/profile/refresh`

Use this when the student clicks retry/refresh, or when the stored report is too
old and the UI wants to force a new Moodle + AI run.

```ts
const response = await fetch(
  `${apiBaseUrl}/api/me/profile/refresh`,
  {
    method: "POST",
    headers: apiHeaders,
    body: JSON.stringify({
      course_id: 2,
      course_name: "Introduction to IT",
      assignment_ids: null,
      quiz_ids: null,
      assessment_weights: null,
      explicit_assignment_mappings: null,
      explicit_quiz_mappings: null,
    }),
  },
);

const refreshedProfile = await response.json();

if (!response.ok) throw refreshedProfile;
```

This POST writes refreshed report data to Supabase through the backend. The
browser still does not write directly to report tables.

#### GET `/api/jobs/{jobId}`

Use this if the backend later changes refreshes to run in the background, or to
show job status after a failed/long refresh.

```ts
const response = await fetch(
  `${apiBaseUrl}/api/jobs/${jobId}`,
  {
    method: "GET",
    headers: apiHeaders,
  },
);

const job = await response.json();
```

Possible job statuses:

```text
not_found
pending
running
ready
failed
```

### Supabase GET Reads For Stored Data

After the backend has linked the student, Mark can safely read stored data
directly from Supabase. RLS ensures the browser only sees rows owned by the
logged-in student.

Get the latest course-profile summary:

```ts
const { data: summaries, error } = await supabase
  .from("student_learning_report_summary")
  .select(`
    student_id,
    moodle_user_id,
    display_name,
    learning_report_id,
    report_key,
    report_type,
    course_moodle_id,
    course_name,
    overall_mastery_score,
    weakest_competencies,
    generated_at,
    updated_at
  `)
  .eq("report_type", "course_learning_profile")
  .eq("course_moodle_id", "2")
  .order("generated_at", { ascending: false })
  .limit(1);

if (error) throw error;

const summary = summaries?.[0] ?? null;
```

Get the full report JSON:

```ts
const { data: reportRow, error } = await supabase
  .from("learning_reports")
  .select(`
    id,
    report_key,
    report_type,
    overall_mastery_score,
    generated_at,
    full_report
  `)
  .eq("id", summary.learning_report_id)
  .maybeSingle();

if (error) throw error;

const report = reportRow?.full_report;
```

Get normalized mastery rows:

```ts
const { data: masteryRows, error } = await supabase
  .from("competency_mastery")
  .select(`
    competency_id,
    title,
    description,
    mastery_score,
    confidence,
    evidence_count,
    total_evidence_weight
  `)
  .eq("learning_report_id", summary.learning_report_id);

if (error) throw error;
```

Get normalized MCQs:

```ts
const { data: quizQuestions, error } = await supabase
  .from("ai_quiz_questions")
  .select(`
    id,
    weak_area,
    question_number,
    question_text,
    choice_1,
    choice_2,
    choice_3,
    correct_answer,
    explanation
  `)
  .eq("learning_report_id", summary.learning_report_id)
  .order("weak_area", { ascending: true })
  .order("question_number", { ascending: true });

if (error) throw error;
```

Get recommendations:

```ts
const { data: recommendations, error } = await supabase
  .from("ai_recommendations")
  .select(`
    title,
    related_area,
    reason,
    action,
    recommendation
  `)
  .eq("learning_report_id", summary.learning_report_id);

if (error) throw error;
```

Get evidence rows if the UI needs an evidence/audit view:

```ts
const { data: evidenceRows, error } = await supabase
  .from("student_evidence")
  .select(`
    source_type,
    assignment_moodle_id,
    quiz_moodle_id,
    competency_code,
    competency_name,
    score,
    max_score,
    normalised_score,
    mapping_source
  `)
  .eq("learning_report_id", summary.learning_report_id);

if (error) throw error;
```

### Frontend POST Writes

For the current MVP, the frontend should not write directly to any SkillSync
report tables.

Allowed browser-side POST/write actions:

```text
Supabase Auth signUp
  Creates the student's auth user.

Supabase Auth signInWithPassword
  Creates a session/access token for the student.

POST /api/me/profile/refresh
  Asks the backend to regenerate and store the student's course profile.
```

Not currently implemented:

```text
Saving MCQ answers
Saving student notes
Saving student completion/checklist state
Writing profile/report/evidence rows directly from the frontend
```

If the frontend later needs to store student MCQ answers or learning-plan
progress, add a new student-owned table and RLS policy first. Do not overload
the AI-generated `ai_quiz_questions` table for student attempts.

### Freshness Logic

Default freshness is 24 hours (`1440` minutes). The frontend may check
`generated_at` to decide whether to call refresh, but the backend remains the
final authority on whether a report is fresh.

Recommended frontend behavior:

```text
After login
  Call GET /api/me/courses and display the returned Moodle courses.

Course selected and no summary/profile exists
  Call GET /api/me/profile?course_id={selectedCourseId}.

Summary exists and generated_at is fresh
  Read learning_reports.full_report and render it.

Summary exists but generated_at is older than 24 hours
  Show stored data immediately if desired, then call POST /api/me/profile/refresh.

Refresh fails
  Keep the old stored report visible if one exists and show a retry option.
```

### Recommended UI States

```text
loading
  The API request is in progress.

generating
  A future async backend may return pending/running with a job_id.

ready
  A learning report is ready to display.

failed
  Generation failed. Show a friendly message and retry button.

empty
  No report/evidence exists yet, or the assignment is not graded.
```

### Fields To Display First

Use these fields for the report header:

```text
overall_mastery_score
generated_at
report.student.name
report.course.course_name
report.included_assessments
```

Use these fields for mastery cards:

```text
report.mastery_report.silo_mastery[].title
report.mastery_report.silo_mastery[].description
report.mastery_report.silo_mastery[].mastery_score
report.mastery_report.silo_mastery[].confidence
report.mastery_report.silo_mastery[].evidence_count
```

Use these fields for weak-area cards:

```text
report.calculated_weak_areas[].title
report.calculated_weak_areas[].mastery_score
report.calculated_weak_areas[].reason
```

Use these fields for AI support:

```text
report.ai_feedback.summary
report.ai_feedback.areas_for_improvement
report.ai_feedback.evidence_based_study_plan
report.ai_feedback.generated_quiz_questions
report.ai_feedback.recommendations
```

### MCQ Display

If the backend returns the full report object, Mark can read MCQs from:

```text
report.ai_feedback.generated_quiz_questions
```

For frontend cards/lists, the normalized Supabase table is easier:

```text
ai_quiz_questions
```

Useful columns:

```text
weak_area
question_number
question_text
choice_1
choice_2
choice_3
correct_answer
explanation
```

Recommended UI behavior:

- Show the question text.
- Render `choice_1`, `choice_2`, and `choice_3` as answer buttons.
- Keep `correct_answer` hidden until the student selects an answer or clicks reveal.
- Show `explanation` after answer submission.

### Frontend Should Not Do

The frontend should not:

- Calculate mastery scores.
- Guess missing competency mappings.
- Send secrets to the browser.
- Let AI text overwrite calculated scores.
- Treat AI-generated MCQs as Moodle grades.
- Write directly to `learning_reports`, `student_evidence`, `competency_mastery`,
  `ai_quiz_questions`, or `ai_recommendations`.

---

## 8. Supabase Storage Contract

The Python repository writes to Supabase using:

```text
repositories/supabase_learning_reports.py
```

Main relationship:

```text
students
  -> learning_reports
      -> competency_mastery
      -> student_evidence
      -> ai_quiz_question_groups
          -> ai_quiz_questions
      -> ai_recommendations

students
  -> report_generation_jobs
```

### Table Purposes

```text
students
  One row per Moodle student. The stable external key is moodle_user_id.

learning_reports
  One latest report per report_key. Stores the full report JSON and summary fields.

competency_mastery
  One row per calculated competency/SILO mastery score.

student_evidence
  One row per normalized evidence item used by the mastery engine.

ai_quiz_question_groups
  Raw AI quiz groups by weak area. Useful for audit/debugging.

ai_quiz_questions
  One frontend-friendly row per generated MCQ.

ai_recommendations
  One frontend-friendly row per recommendation.

report_generation_jobs
  Tracks pending/running/ready/failed generation lifecycle.
```

### Student Association

Every report is associated with a specific student in two ways:

```text
students.moodle_user_id
learning_reports.student_id -> students.id
```

Child tables connect through:

```text
learning_report_id -> learning_reports.id
```

That means all mastery rows, evidence rows, MCQs, recommendations, and job rows
can be traced back to the specific student.

### RLS/Security Note

RLS is enabled on the tables and student-owned SELECT policies are active.

Current MVP access pattern:

```text
Frontend -> Supabase Auth
Frontend -> Supabase reads with anon/publishable key + student access token
Frontend -> Python Backend API for refresh/job actions
Python Backend API -> Moodle, AI provider, and Supabase service role
```

The frontend may read the student-owned tables listed above with the
anon/publishable key. RLS uses `students.auth_user_id = auth.uid()` so the
browser only sees rows for the logged-in student.

The frontend must never use the service-role key and must not write directly to
SkillSync report tables.

---

## 9. Suggested Frontend Data Pattern

For a report page, the frontend can either:

1. Use the full `report` object returned by the FastAPI profile endpoints.
2. Query normalized Supabase child tables after finding `learning_report_id`.

Suggested query sequence if using normalized tables:

```text
1. Find latest report:
   learning_reports where report_key = ...

2. Fetch mastery rows:
   competency_mastery where learning_report_id = ...

3. Fetch evidence rows:
   student_evidence where learning_report_id = ...

4. Fetch quiz rows:
   ai_quiz_questions where learning_report_id = ...

5. Fetch recommendations:
   ai_recommendations where learning_report_id = ...
```

The full JSON report is still stored in:

```text
learning_reports.full_report
```

That is useful for quick MVP integration because it already contains everything
needed for the frontend.

---

## 10. Frontend API Smoke Checks

Use the hosted API base URL unless testing a local API:

```powershell
$apiBaseUrl = "https://api.skillsynch.org"
```

Health check:

```powershell
Invoke-WebRequest "$apiBaseUrl/health" -UseBasicParsing
```

Authenticated endpoints need a Supabase Auth access token from the logged-in
frontend session:

```powershell
$accessToken = "<supabase-access-token>"
Invoke-WebRequest "$apiBaseUrl/api/me/courses" -Headers @{ Authorization = "Bearer $accessToken" } -UseBasicParsing
```

---

## 11. Production Notes

### MVP Shape

Current implementation is synchronous:

```text
Backend request waits while Moodle, mastery, AI, and Supabase save complete.
```

This is acceptable for Capstone MVP testing, but AI calls can be slow.

### More Production-Ready Shape

Future API work can change refreshes to:

```text
POST refresh request
  -> create job
  -> return 202 + job_id
  -> background worker runs Python pipeline
  -> frontend polls GET /jobs/{jobId}
```

The `report_generation_jobs` table already supports this future worker pattern.

### Error Handling

Common failures the backend should surface clearly:

```text
Moodle token missing or invalid
Moodle external function not enabled
Assignment not found
Assignment not graded
Rubric criteria missing
Competency mapping missing
AI provider API failure
Supabase service-role key missing
Supabase save failure
```

### Current Limitations

```text
Only the latest report per report_key is stored in learning_reports.
Historical report versions would require a separate report history table.
Student MCQ answer/progress storage is not implemented yet.
Refresh is synchronous for the MVP, so long AI calls may keep the request open.
```

---