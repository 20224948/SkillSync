/*
|--------------------------------------------------------------------------
| SkillSync Backend API Configuration
|--------------------------------------------------------------------------
| This file contains helper functions for calling the hosted SkillSync API.
| Authenticated requests must include the Supabase access token.
|--------------------------------------------------------------------------
*/

const API_BASE_URL = process.env.NEXT_PUBLIC_SKILLSYNC_API_BASE_URL

if (!API_BASE_URL) {
  throw new Error('Missing NEXT_PUBLIC_SKILLSYNC_API_BASE_URL')
}

export async function getCourses(accessToken: string) {
  const response = await fetch(`${API_BASE_URL}/api/me/courses`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  const data = await response.json()

  if (!response.ok) {
    throw data
  }

  return data
}

export async function getCourseProfile(accessToken: string, courseId: number) {
  const response = await fetch(
    `${API_BASE_URL}/api/me/profile?course_id=${courseId}`,
    {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw data
  }

  return data
}