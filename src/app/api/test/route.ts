import { NextResponse } from 'next/server'

/*
|--------------------------------------------------------------------------
| Test API Endpoint
|--------------------------------------------------------------------------
| Simple development/testing endpoint used during early frontend integration.
| Returns a mock SkillSync response structure for UI testing purposes.
|--------------------------------------------------------------------------
*/

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