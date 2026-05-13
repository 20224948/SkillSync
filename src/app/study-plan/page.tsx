'use client'

import { useEffect, useState } from 'react'

import { getStudyPlanData } from '../lib/api'

export default function StudyPlanPage() {
  /*
  |--------------------------------------------------------------------------
  | Component State
  |--------------------------------------------------------------------------
  */

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState<any>(null)

  /*
  |--------------------------------------------------------------------------
  | Load Study Plan Data
  |--------------------------------------------------------------------------
  | Retrieves AI-generated study plan recommendations for the
  | logged-in student's latest learning report.
  |--------------------------------------------------------------------------
  */

  useEffect(() => {
    async function loadStudyPlan() {
      try {
        const result = await getStudyPlanData()

        setData(result)
      } catch (error: any) {
        setError(error?.message || 'Failed to load study plan')
      } finally {
        setLoading(false)
      }
    }

    loadStudyPlan()
  }, [])

  /*
  |--------------------------------------------------------------------------
  | Loading / Error States
  |--------------------------------------------------------------------------
  */

  if (loading) return <p>Loading study plan...</p>

  if (error) return <p>Error: {error}</p>

  const firstName =
    data?.student?.display_name?.split(' ')[0] || 'Student'

  const recommendations = data?.recommendations ?? []

  return (
    <div>
      {/* Page header */}
      <div className="page-heading">
        <h1>{firstName}&apos;s Study Plan</h1>

        <p>
          Your personalised study plan based on identified skill gaps
        </p>
      </div>

      {/* Empty state */}
      {recommendations.length === 0 ? (
        <div className="empty-state">
          <p>No study plan actions available yet.</p>
        </div>
      ) : (
        <div className="study-plan-grid">
          {recommendations.map((item: any, index: number) => (
            <div className="study-plan-card" key={item.id}>
              <h3>{item.title || `Study Focus ${index + 1}`}</h3>

              <p>{item.action}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}