import { supabase } from './supabaseClient'

export async function getStudentData() {
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession()

  if (sessionError || !session?.user) {
    throw new Error('No active Supabase session found')
  }

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
    .order('generated_at', { ascending: false })

  if (reportsError) throw new Error(reportsError.message)

  if (!reports || reports.length === 0) {
    return {
      status: 'empty',
      student,
      reports: [],
      masteryRows: [],
      overall_mastery_score: null,
      generated_at: null,
    }
  }

  const learningReportIds = reports.map((report) => report.id)

  const { data: masteryRows, error: masteryError } = await supabase
    .from('competency_mastery')
    .select(`
      learning_report_id,
      competency_id,
      title,
      description,
      mastery_score,
      confidence,
      evidence_count,
      total_evidence_weight
    `)
    .in('learning_report_id', learningReportIds)

  if (masteryError) throw new Error(masteryError.message)

  const reportMap = new Map(
    reports.map((report) => [
      report.id,
      {
        course_name: report.course_name,
        course_moodle_id: report.course_moodle_id,
      },
    ])
  )

  const groupedMastery = new Map()

  for (const row of masteryRows ?? []) {
    const reportInfo = reportMap.get(row.learning_report_id)

    const groupKey = `${row.learning_report_id}-${row.competency_id}`

    const existing = groupedMastery.get(groupKey)

    if (!existing) {
      groupedMastery.set(groupKey, {
        learning_report_id: row.learning_report_id,
        competency_id: row.competency_id,
        course_name:
          reportInfo?.course_name ?? 'Unknown Course',
        course_moodle_id:
          reportInfo?.course_moodle_id ?? null,
        title: row.title,
        description: row.description,
        confidence: row.confidence,
        mastery_score: Number(row.mastery_score),
        evidence_count: Number(row.evidence_count ?? 0),
        total_evidence_weight: Number(
          row.total_evidence_weight ?? 0
        ),
        report_count: 1,
      })

      continue
    }

    existing.mastery_score += Number(row.mastery_score)
    existing.evidence_count += Number(row.evidence_count ?? 0)
    existing.total_evidence_weight += Number(
      row.total_evidence_weight ?? 0
    )
    existing.report_count += 1
  }

  const aggregatedMasteryRows = Array.from(
    groupedMastery.values()
  ).map((row: any) => ({
    ...row,
    mastery_score: row.mastery_score / row.report_count,
  }))

  const overall_mastery_score =
    reports.reduce(
      (sum, report) =>
        sum + Number(report.overall_mastery_score ?? 0),
      0
    ) / reports.length

  return {
    status: 'ready',
    student,
    reports,
    masteryRows: aggregatedMasteryRows,
    overall_mastery_score,
    generated_at: reports[0]?.generated_at ?? null,
  }
}

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
    .order('created_at', { ascending: true })

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
    .order('created_at', { ascending: true })

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
    .order('weak_area', { ascending: true })
    .order('question_number', { ascending: true })

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