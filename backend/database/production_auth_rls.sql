-- Production auth linkage and student-owned read policies.

alter table public.students
    add column if not exists auth_user_id uuid references auth.users(id) on delete set null;

alter table public.students
    add column if not exists email text;

create unique index if not exists students_auth_user_id_key
    on public.students(auth_user_id)
    where auth_user_id is not null;

create index if not exists idx_students_lower_email
    on public.students((lower(email)));

alter table public.students enable row level security;
alter table public.learning_reports enable row level security;
alter table public.competency_mastery enable row level security;
alter table public.student_evidence enable row level security;
alter table public.ai_quiz_question_groups enable row level security;
alter table public.ai_quiz_questions enable row level security;
alter table public.ai_recommendations enable row level security;
alter table public.report_generation_jobs enable row level security;

grant usage on schema public to authenticated;

grant select on
    public.students,
    public.learning_reports,
    public.competency_mastery,
    public.student_evidence,
    public.ai_quiz_question_groups,
    public.ai_quiz_questions,
    public.ai_recommendations,
    public.report_generation_jobs,
    public.student_learning_report_summary
to authenticated;

revoke all on
    public.students,
    public.learning_reports,
    public.competency_mastery,
    public.student_evidence,
    public.ai_quiz_question_groups,
    public.ai_quiz_questions,
    public.ai_recommendations,
    public.report_generation_jobs
from anon;

revoke insert, update, delete on
    public.students,
    public.learning_reports,
    public.competency_mastery,
    public.student_evidence,
    public.ai_quiz_question_groups,
    public.ai_quiz_questions,
    public.ai_recommendations,
    public.report_generation_jobs
from authenticated;

drop policy if exists students_select_own on public.students;
create policy students_select_own
on public.students
for select
to authenticated
using ((select auth.uid()) = auth_user_id);

drop policy if exists learning_reports_select_own on public.learning_reports;
create policy learning_reports_select_own
on public.learning_reports
for select
to authenticated
using (
    exists (
        select 1
        from public.students s
        where s.id = learning_reports.student_id
            and s.auth_user_id = (select auth.uid())
    )
);

drop policy if exists competency_mastery_select_own on public.competency_mastery;
create policy competency_mastery_select_own
on public.competency_mastery
for select
to authenticated
using (
    exists (
        select 1
        from public.learning_reports lr
        join public.students s on s.id = lr.student_id
        where lr.id = competency_mastery.learning_report_id
            and s.auth_user_id = (select auth.uid())
    )
);

drop policy if exists student_evidence_select_own on public.student_evidence;
create policy student_evidence_select_own
on public.student_evidence
for select
to authenticated
using (
    exists (
        select 1
        from public.learning_reports lr
        join public.students s on s.id = lr.student_id
        where lr.id = student_evidence.learning_report_id
            and s.auth_user_id = (select auth.uid())
    )
);

drop policy if exists ai_quiz_question_groups_select_own on public.ai_quiz_question_groups;
create policy ai_quiz_question_groups_select_own
on public.ai_quiz_question_groups
for select
to authenticated
using (
    exists (
        select 1
        from public.learning_reports lr
        join public.students s on s.id = lr.student_id
        where lr.id = ai_quiz_question_groups.learning_report_id
            and s.auth_user_id = (select auth.uid())
    )
);

drop policy if exists ai_quiz_questions_select_own on public.ai_quiz_questions;
create policy ai_quiz_questions_select_own
on public.ai_quiz_questions
for select
to authenticated
using (
    exists (
        select 1
        from public.learning_reports lr
        join public.students s on s.id = lr.student_id
        where lr.id = ai_quiz_questions.learning_report_id
            and s.auth_user_id = (select auth.uid())
    )
);

drop policy if exists ai_recommendations_select_own on public.ai_recommendations;
create policy ai_recommendations_select_own
on public.ai_recommendations
for select
to authenticated
using (
    exists (
        select 1
        from public.learning_reports lr
        join public.students s on s.id = lr.student_id
        where lr.id = ai_recommendations.learning_report_id
            and s.auth_user_id = (select auth.uid())
    )
);

drop policy if exists report_generation_jobs_select_own on public.report_generation_jobs;
create policy report_generation_jobs_select_own
on public.report_generation_jobs
for select
to authenticated
using (
    exists (
        select 1
        from public.students s
        where s.id = report_generation_jobs.student_id
            and s.auth_user_id = (select auth.uid())
    )
);
