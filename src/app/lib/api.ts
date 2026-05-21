import { supabase } from './supabaseClient'

/*
|--------------------------------------------------------------------------
| Student Dashboard Data
|--------------------------------------------------------------------------
*/

export async function getStudentData() {
  /*
  |--------------------------------------------------------------------------
  | Current Session
  |--------------------------------------------------------------------------
  */

  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession()

  if (sessionError || !session?.user) {
    throw new Error('No active Supabase session found')
  }

  /*
  |--------------------------------------------------------------------------
  | Current Student
  |--------------------------------------------------------------------------
  */

  const authUserId = session.user.id

  const { data: student, error: studentError } = await supabase
    .from('students')
    .select(`
      id,
      display_name,
      moodle_user_id,
      auth_user_id
    `)
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
  | Learning Reports
  |--------------------------------------------------------------------------
  */

  const { data: reports, error: reportsError } = await supabase
    .from('learning_reports')
    .select(`
      id,
      course_moodle_id,
      course_name,
      overall_mastery_score,
      generated_at
    `)
    .eq('student_id', student.id)
    .order('generated_at', { ascending: false })

  if (reportsError) throw new Error(reportsError.message)

  if (!reports || reports.length === 0) {
    return {
      status: 'empty',
      student,
      reports: [],
      masteryRows: [],
      overall_mastery_score: 0,
    }
  }

  /*
  |--------------------------------------------------------------------------
  | Latest + Previous Reports Per Course
  |--------------------------------------------------------------------------
  */

  const reportsByCourse = new Map()

  for (const report of reports) {
    const courseId = report.course_moodle_id

    if (!reportsByCourse.has(courseId)) {
      reportsByCourse.set(courseId, [])
    }

    reportsByCourse.get(courseId).push(report)
  }

  const latestReports = Array.from(
    reportsByCourse.values()
  ).map((courseReports: any[]) => courseReports[0])

  const previousReports = Array.from(
    reportsByCourse.values()
  )
    .map((courseReports: any[]) => courseReports[1])
    .filter(Boolean)

  const latestReportIds = latestReports.map(
    (report) => report.id
  )

  const previousReportIds = previousReports.map(
    (report) => report.id
  )

  /*
  |--------------------------------------------------------------------------
  | Current Mastery Data
  |--------------------------------------------------------------------------
  */

  const {
    data: currentMasteryRows,
    error: masteryError,
  } = await supabase
    .from('competency_mastery')
    .select(`
      learning_report_id,
      competency_id,
      title,
      description,
      mastery_score,
      confidence
    `)
    .in('learning_report_id', latestReportIds)

  if (masteryError) throw new Error(masteryError.message)

  /*
  |--------------------------------------------------------------------------
  | Previous Mastery Data
  |--------------------------------------------------------------------------
  */

  let previousMasteryRows: any[] = []

  if (previousReportIds.length > 0) {
    const {
      data,
      error: previousError,
    } = await supabase
      .from('competency_mastery')
      .select(`
        learning_report_id,
        competency_id,
        mastery_score
      `)
      .in('learning_report_id', previousReportIds)

    if (previousError) {
      throw new Error(previousError.message)
    }

    previousMasteryRows = data ?? []
  }

  /*
  |--------------------------------------------------------------------------
  | Report Metadata
  |--------------------------------------------------------------------------
  */

  const reportMap = new Map(
    latestReports.map((report) => [
      report.id,
      {
        course_name: report.course_name,
        course_moodle_id: report.course_moodle_id,
      },
    ])
  )

  /*
  |--------------------------------------------------------------------------
  | Previous Score Lookup
  |--------------------------------------------------------------------------
  */

  const previousScoreMap = new Map()

  for (const row of previousMasteryRows) {
    previousScoreMap.set(
      `${row.competency_id}`,
      Number(row.mastery_score)
    )
  }

  /*
  |--------------------------------------------------------------------------
  | Dashboard Rows
  |--------------------------------------------------------------------------
  */

  const masteryRows = (currentMasteryRows ?? []).map(
    (row: any) => {
      const reportInfo = reportMap.get(
        row.learning_report_id
      )

      const previousScore =
        previousScoreMap.get(row.competency_id) ?? null

      const currentScore = Number(row.mastery_score)

      return {
        learning_report_id: row.learning_report_id,
        competency_id: row.competency_id,

        course_name:
          reportInfo?.course_name ?? 'Unknown Course',

        course_moodle_id:
          reportInfo?.course_moodle_id ?? null,

        title: row.title,
        description: row.description,
        confidence: row.confidence,

        mastery_score: currentScore,

        previous_mastery_score: previousScore,

        mastery_change:
          previousScore !== null
            ? currentScore - previousScore
            : null,
      }
    }
  )

  /*
  |--------------------------------------------------------------------------
  | Overall Mastery
  |--------------------------------------------------------------------------
  */

  const overall_mastery_score =
  masteryRows.reduce(
    (sum, row) => sum + Number(row.mastery_score),
    0
  ) / masteryRows.length

  return {
    status: 'ready',
    student,
    reports: latestReports,
    masteryRows,
    overall_mastery_score,
  }
}

/*
|--------------------------------------------------------------------------
| Study Plan
|--------------------------------------------------------------------------
*/

export async function getStudyPlanData() {
  const studentData = await getStudentData()

  if (!studentData.reports.length) {
    return {
      student: studentData.student,
      recommendations: [],
    }
  }

  const reportIds = studentData.reports.map(
    (report) => report.id
  )

  const { data: recommendations, error } = await supabase
    .from('ai_recommendations')
    .select(`
      learning_report_id,
      title,
      related_area,
      reason,
      action
    `)
    .in('learning_report_id', reportIds)

  if (error) throw new Error(error.message)

  const reportMap = new Map(
    studentData.reports.map((report) => [
      report.id,
      report.course_name,
    ])
  )

  const recommendationsWithCourse = (
    recommendations ?? []
  ).map((item) => ({
    ...item,
    course_name:
      reportMap.get(item.learning_report_id) ??
      'Unknown Course',
  }))

  return {
    student: studentData.student,
    recommendations: recommendationsWithCourse,
  }
}

/*
|--------------------------------------------------------------------------
| Study Tips
|--------------------------------------------------------------------------
*/

export async function getStudyTipsData() {
  const studentData = await getStudentData()

  if (!studentData.reports.length) {
    return {
      student: studentData.student,
      tips: [],
    }
  }

  const reportIds = studentData.reports.map(
    (report) => report.id
  )

  const { data: tips, error } = await supabase
    .from('ai_recommendations')
    .select(`
      learning_report_id,
      title,
      related_area,
      recommendation
    `)
    .in('learning_report_id', reportIds)

  if (error) throw new Error(error.message)

  const reportMap = new Map(
    studentData.reports.map((report) => [
      report.id,
      report.course_name,
    ])
  )

  const tipsWithCourse = (tips ?? []).map((tip) => ({
    ...tip,
    course_name:
      reportMap.get(tip.learning_report_id) ??
      'Unknown Course',
  }))

  return {
    student: studentData.student,
    tips: tipsWithCourse,
  }
}

/*
|--------------------------------------------------------------------------
| Adaptive Quiz
|--------------------------------------------------------------------------
*/

export async function getAdaptiveQuizData() {
  const studentData = await getStudentData()

  if (!studentData.reports.length) {
    return {
      student: studentData.student,
      questions: [],
    }
  }

  const reportIds = studentData.reports.map(
    (report) => report.id
  )

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
    .in('learning_report_id', reportIds)

  if (error) throw new Error(error.message)

  const reportMap = new Map(
    studentData.reports.map((report) => [
      report.id,
      report.course_name,
    ])
  )

  const questionsWithCourse = (questions ?? []).map(
    (question) => ({
      ...question,
      course_name:
        reportMap.get(question.learning_report_id) ??
        'Unknown Course',
    })
  )

  return {
    student: studentData.student,
    questions: questionsWithCourse,
  }
}