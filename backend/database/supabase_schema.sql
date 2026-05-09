-- SkillSync AI learning report schema for Supabase.
--
-- Apply this in Supabase SQL Editor, or through deployment tooling when available.
-- The Python repository writes one latest report per student/course/assignment
-- using learning_reports.report_key as the upsert key.

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create table if not exists public.students (
    id uuid primary key default gen_random_uuid(),
    moodle_user_id text not null unique,
    auth_user_id uuid references auth.users(id) on delete set null,
    display_name text,
    email text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

drop trigger if exists set_students_updated_at on public.students;

create trigger set_students_updated_at
before update on public.students
for each row
execute function public.set_updated_at();

create table if not exists public.learning_reports (
    id uuid primary key default gen_random_uuid(),
    report_key text not null unique,
    report_type text not null default 'assignment_learning_report',
    schema_version text not null default '1.0',

    student_id uuid not null references public.students(id) on delete restrict,
    student_moodle_user_id text not null,
    student_name text,

    course_moodle_id text not null,
    course_name text,

    assignment_moodle_id text,
    assignment_name text,
    course_module_id text,
    included_assessments jsonb not null default '[]'::jsonb,

    overall_mastery_score numeric,
    weakest_competencies jsonb not null default '[]'::jsonb,

    mastery_report jsonb not null,
    ai_feedback jsonb not null,
    evidence jsonb not null default '[]'::jsonb,
    full_report jsonb not null,

    ai_provider text,
    ai_model text,

    generated_at timestamptz not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.competency_mastery (
    id uuid primary key default gen_random_uuid(),
    learning_report_id uuid not null references public.learning_reports(id) on delete cascade,

    competency_id text not null,
    title text,
    description text,
    mastery_score numeric,
    confidence text,
    evidence_count integer,
    total_evidence_weight numeric,
    evidence jsonb not null default '[]'::jsonb,

    created_at timestamptz not null default now()
);

create table if not exists public.student_evidence (
    id uuid primary key default gen_random_uuid(),
    learning_report_id uuid not null references public.learning_reports(id) on delete cascade,

    source_type text not null,
    assignment_moodle_id text,
    quiz_moodle_id text,
    quiz_attempt_id text,
    course_module_id text,
    criterion_id text,

    competency_id text,
    competency_code text,
    competency_name text,

    score numeric,
    max_score numeric,
    normalised_score numeric,
    feedback text,
    mapping_source text,
    evidence jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now()
);

create table if not exists public.ai_quiz_question_groups (
    id uuid primary key default gen_random_uuid(),
    learning_report_id uuid not null references public.learning_reports(id) on delete cascade,

    weak_area text,
    questions jsonb not null default '[]'::jsonb,

    created_at timestamptz not null default now()
);

create table if not exists public.ai_quiz_questions (
    id uuid primary key default gen_random_uuid(),
    question_group_id uuid references public.ai_quiz_question_groups(id) on delete cascade,
    learning_report_id uuid not null references public.learning_reports(id) on delete cascade,

    weak_area text,
    question_number integer,
    question_text text not null,
    choice_1 text,
    choice_2 text,
    choice_3 text,
    correct_answer text,
    explanation text,
    question_payload jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now()
);

create table if not exists public.ai_recommendations (
    id uuid primary key default gen_random_uuid(),
    learning_report_id uuid not null references public.learning_reports(id) on delete cascade,

    title text,
    related_area text,
    reason text,
    action text,
    recommendation jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now()
);

create table if not exists public.report_generation_jobs (
    id uuid primary key default gen_random_uuid(),
    report_key text not null,
    student_id uuid references public.students(id) on delete set null,
    student_moodle_user_id text not null,
    course_moodle_id text not null,
    assignment_moodle_id text,
    report_type text not null default 'assignment_learning_report',
    learning_report_id uuid references public.learning_reports(id) on delete set null,

    status text not null check (status in ('pending', 'running', 'ready', 'failed')),
    source text,
    force_refresh boolean not null default false,
    error_message text,

    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

drop trigger if exists set_report_generation_jobs_updated_at on public.report_generation_jobs;

create trigger set_report_generation_jobs_updated_at
before update on public.report_generation_jobs
for each row
execute function public.set_updated_at();

alter table public.learning_reports
    add column if not exists report_type text not null default 'assignment_learning_report';

alter table public.learning_reports
    add column if not exists included_assessments jsonb not null default '[]'::jsonb;

alter table public.students
    add column if not exists auth_user_id uuid references auth.users(id) on delete set null;

alter table public.students
    add column if not exists email text;

alter table public.student_evidence
    add column if not exists quiz_moodle_id text;

alter table public.student_evidence
    add column if not exists quiz_attempt_id text;

alter table public.student_evidence
    add column if not exists course_module_id text;

alter table public.report_generation_jobs
    add column if not exists report_type text not null default 'assignment_learning_report';

alter table public.report_generation_jobs
    alter column assignment_moodle_id drop not null;

create index if not exists idx_learning_reports_student
    on public.learning_reports(student_moodle_user_id);

create unique index if not exists students_auth_user_id_key
    on public.students(auth_user_id)
    where auth_user_id is not null;

create index if not exists idx_students_lower_email
    on public.students((lower(email)));

create index if not exists idx_learning_reports_report_type
    on public.learning_reports(report_type);

create index if not exists idx_learning_reports_student_id
    on public.learning_reports(student_id);

create index if not exists idx_learning_reports_course
    on public.learning_reports(course_moodle_id);

create index if not exists idx_learning_reports_assignment
    on public.learning_reports(assignment_moodle_id);

create index if not exists idx_competency_mastery_report
    on public.competency_mastery(learning_report_id);

create index if not exists idx_student_evidence_report
    on public.student_evidence(learning_report_id);

create index if not exists idx_student_evidence_quiz
    on public.student_evidence(quiz_moodle_id);

create index if not exists idx_ai_quiz_question_groups_report
    on public.ai_quiz_question_groups(learning_report_id);

create index if not exists idx_ai_quiz_questions_report
    on public.ai_quiz_questions(learning_report_id);

create index if not exists idx_ai_quiz_questions_group
    on public.ai_quiz_questions(question_group_id);

create index if not exists idx_ai_recommendations_report
    on public.ai_recommendations(learning_report_id);

create index if not exists idx_report_generation_jobs_report_key
    on public.report_generation_jobs(report_key);

create index if not exists idx_report_generation_jobs_report_type
    on public.report_generation_jobs(report_type);

create index if not exists idx_report_generation_jobs_learning_report_id
    on public.report_generation_jobs(learning_report_id);

create index if not exists idx_report_generation_jobs_student
    on public.report_generation_jobs(student_id);

create index if not exists idx_report_generation_jobs_status
    on public.report_generation_jobs(status);

create index if not exists idx_report_generation_jobs_created_at
    on public.report_generation_jobs(created_at desc);

drop trigger if exists set_learning_reports_updated_at on public.learning_reports;

create trigger set_learning_reports_updated_at
before update on public.learning_reports
for each row
execute function public.set_updated_at();

drop view if exists public.student_learning_report_summary;

create view public.student_learning_report_summary
with (security_invoker = true) as
select
    s.id as student_id,
    s.moodle_user_id,
    s.display_name,
    lr.id as learning_report_id,
    lr.report_key,
    lr.report_type,
    lr.course_moodle_id,
    lr.course_name,
    lr.assignment_moodle_id,
    lr.assignment_name,
    lr.overall_mastery_score,
    lr.weakest_competencies,
    lr.ai_provider,
    lr.ai_model,
    lr.generated_at,
    lr.updated_at
from public.students s
join public.learning_reports lr
    on lr.student_id = s.id;

-- Keep RLS enabled so student learning data is not accidentally exposed through
-- the public anon key. The Python backend uses the service role key, which
-- bypasses RLS. If Mark's frontend needs direct Supabase reads later, add
-- narrow SELECT policies for the correct authenticated users.
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
