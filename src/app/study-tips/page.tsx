'use client'

import { useEffect, useState } from 'react'

import { getStudyTipsData } from '../lib/api'

export default function StudyTipsPage() {
  /*
  |--------------------------------------------------------------------------
  | Component State
  |--------------------------------------------------------------------------
  */

  const [student, setStudent] = useState<any>(null)
  const [tips, setTips] = useState<any[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  /*
  |--------------------------------------------------------------------------
  | Load Study Tips Data
  |--------------------------------------------------------------------------
  | Retrieves AI-generated study tips connected to the student's
  | latest learning report.
  |--------------------------------------------------------------------------
  */

  useEffect(() => {
    async function loadStudyTips() {
      try {
        const data = await getStudyTipsData()

        setStudent(data.student)
        setTips(data.tips)
      } catch (error: any) {
        setError(error?.message || 'Failed to load study tips')
      } finally {
        setLoading(false)
      }
    }

    loadStudyTips()
  }, [])

  /*
  |--------------------------------------------------------------------------
  | Loading / Error States
  |--------------------------------------------------------------------------
  */

  if (loading) return <p>Loading study tips...</p>

  if (error) return <p>Error: {error}</p>

  return (
    <div>
      {/* Page header */}
      <div className="page-heading">
        <h1>Study Tips</h1>

        <p>
          Here are personalised tips for {student?.display_name}.
        </p>
      </div>

      {/* Empty state */}
      {tips.length === 0 ? (
        <div className="empty-state">
          <p>No tips available yet.</p>
        </div>
      ) : (
        <div className="study-tips-list">
          {tips.map((tip: any) => (
            <div className="study-tip-row" key={tip.id}>
              <h3>{tip.title}</h3>

              <span className="study-tip-subtitle">
                {tip.related_area}
              </span>

              <p>{tip.recommendation?.reason}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}