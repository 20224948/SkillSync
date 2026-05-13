import { supabase } from './supabaseClient'

/*
|--------------------------------------------------------------------------
| Student Report Data
|--------------------------------------------------------------------------
| Gets the currently logged-in student and their latest learning report
| for the selected Moodle course.
|--------------------------------------------------------------------------
*/

export async function getStudentData(courseId = '2') {
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession()

  if (sessionError || !session?.user) {
    throw new Error('No active Supabase session found')
  }

  const authUserId = session.user.id

  /*
  |--------------------------------------------------------------------------
  | Logged-In Student
  |--------------------------------------------------------------------------
  | Links the Supabase authenticated user to the matching student row.
  |--------------------------------------------------------------------------
  */

  const { data: student, error: studentError } = await supabase
    .from('students')
    .select('id, display_name, moodle_user_id, auth_user_id')
    .eq('auth_user_id', authUserId)
    .maybeSingle()

  if (studentError) throw new Error(studentError.message)

  if (!student) {
    throw new Error(
      `No student row linked to logged-in user (${session.user.email})`
    )
  }

  /*
  |--------------------------------------------------------------------------
  | Latest Learning Reports
  |--------------------------------------------------------------------------
  | Retrieves the latest report and, where available, the previous report.
  | The previous report is used only to calculate mastery score changes.
  |--------------------------------------------------------------------------
  */

  const { data: reports, error: reportsError } = await supabase
    .from('learning_reports')
    .select(`
      id,
      report_key,
      report_type,
      course_moodle_id,
      course_name,
      overall_mastery_score,
      generated_at,
      full_report
    `)
    .eq('student_id', student.id)
    .eq('course_moodle_id', courseId)
    .order('generated_at', { ascending: false })
    .limit(2)

  if (reportsError) throw new Error(reportsError.message)

  if (!reports || reports.length === 0) {
    throw new Error(`No learning report found for ${student.display_name}`)
  }

  const latestReport = reports[0]
  const previousReport = reports[1] ?? null

  /*
  |--------------------------------------------------------------------------
  | Latest Mastery Rows
  |--------------------------------------------------------------------------
  | Reads the calculated competency/SILO mastery scores from Supabase.
  | These values are calculated by the backend, not by the frontend.
  |--------------------------------------------------------------------------
  */

  const { data: latestMasteryRows, error: latestMasteryError } = await supabase
    .from('competency_mastery')
    .select(`
      competency_id,
      title,
      description,
      mastery_score,
      confidence,
      evidence_count,
      total_evidence_weight
    `)
    .eq('learning_report_id', latestReport.id)
    .order('competency_id', { ascending: true })

  if (latestMasteryError) throw new Error(latestMasteryError.message)

  /*
  |--------------------------------------------------------------------------
  | Previous Mastery Rows
  |--------------------------------------------------------------------------
  | If an older report exists, its scores are loaded so the dashboard
  | can show whether each mastery area has improved or declined.
  |--------------------------------------------------------------------------
  */

  let previousMasteryRows: any[] = []

  if (previousReport) {
    const { data, error } = await supabase
      .from('competency_mastery')
      .select(`
        competency_id,
        title,
        mastery_score
      `)
      .eq('learning_report_id', previousReport.id)

    if (error) throw new Error(error.message)

    previousMasteryRows = data ?? []
  }

  /*
  |--------------------------------------------------------------------------
  | Mastery Trend Mapping
  |--------------------------------------------------------------------------
  | Adds previous score and score-change values to the latest mastery rows.
  | This supports frontend trend indicators without recalculating mastery.
  |--------------------------------------------------------------------------
  */

  const masteryRowsWithTrend =
    latestMasteryRows?.map((current) => {
      const previous = previousMasteryRows.find(
        (item) => item.competency_id === current.competency_id
      )

      const previousScore =
        previous?.mastery_score !== undefined
          ? Number(previous.mastery_score)
          : null

      const currentScore = Number(current.mastery_score)

      return {
        ...current,
        previous_mastery_score: previousScore,
        mastery_change:
          previousScore === null ? null : currentScore - previousScore,
      }
    }) ?? []

  return {
    status: 'ready',
    student,
    masteryRows: masteryRowsWithTrend,
    previous_report_id: previousReport?.id ?? null,
    learning_report_id: latestReport.id,
    overall_mastery_score: latestReport.overall_mastery_score,
    generated_at: latestReport.generated_at,
    report: latestReport.full_report,
  }
}

/*
|--------------------------------------------------------------------------
| Study Plan Data
|--------------------------------------------------------------------------
| Reads AI-generated study recommendations for the latest report.
|--------------------------------------------------------------------------
*/

export async function getStudyPlanData(courseId = '2') {
  const studentData = await getStudentData(courseId)

  const { data: recommendations, error } = await supabase
    .from('ai_recommendations')
    .select(`
      id,
      title,
      related_area,
      reason,
      action
    `)
    .eq('learning_report_id', studentData.learning_report_id)
    .order('created_at', { ascending: true })

  if (error) throw new Error(error.message)

  return {
    student: studentData.student,
    recommendations: recommendations ?? [],
  }
}

/*
|--------------------------------------------------------------------------
| Study Tips Data
|--------------------------------------------------------------------------
| Reads AI-generated study tips connected to the latest report.
|--------------------------------------------------------------------------
*/

export async function getStudyTipsData(courseId = '2') {
  const studentData = await getStudentData(courseId)

  const { data: tips, error } = await supabase
    .from('ai_recommendations')
    .select(`
      id,
      title,
      related_area,
      recommendation
    `)
    .eq('learning_report_id', studentData.learning_report_id)
    .order('created_at', { ascending: true })

  if (error) throw new Error(error.message)

  return {
    student: studentData.student,
    tips: tips ?? [],
  }
}

/*
|--------------------------------------------------------------------------
| Adaptive Quiz Data
|--------------------------------------------------------------------------
| Reads generated quiz questions connected to the latest report.
|--------------------------------------------------------------------------
*/

export async function getAdaptiveQuizData(courseId = '2') {
  const studentData = await getStudentData(courseId)

  const { data: questions, error } = await supabase
    .from('ai_quiz_questions')
    .select(`
      id,
      learning_report_id,
      weak_area,
      question_number,
      question_text,
      choice_1,
      choice_2,
      choice_3,
      correct_answer,
      explanation
    `)
    .eq('learning_report_id', studentData.learning_report_id)
    .order('weak_area', { ascending: true })
    .order('question_number', { ascending: true })

  if (error) throw new Error(error.message)

  return {
    student: studentData.student,
    questions: questions ?? [],
  }
}