import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    name: 'Student',
    mastery: null,
    strengths: [],
    weaknesses: [],
    progress: [],
    studyPlan: [],
    studyTips: [],
    adaptiveQuiz: [],
  })
}