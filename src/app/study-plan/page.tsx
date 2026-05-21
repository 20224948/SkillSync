'use client'

import { useEffect, useState } from 'react'
import { getStudyPlanData } from '../lib/api'

interface StudyPlanItem {
  learning_report_id: string
  title: string
  related_area: string
  reason: string
  action: string
  course_name: string
}

export default function StudyPlanPage() {
  const [recommendations, setRecommendations] = useState<StudyPlanItem[]>([])
  const [studentName, setStudentName] = useState('Student')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadStudyPlan() {
      try {
        setLoading(true)

        const data = await getStudyPlanData()

        setRecommendations(data.recommendations ?? [])
        setStudentName(data.student?.display_name ?? 'Student')
      } catch (err: any) {
        console.error(err)
        setError(err.message || 'Failed to load study plan')
      } finally {
        setLoading(false)
      }
    }

    loadStudyPlan()
  }, [])

  if (loading) {
    return (
      <div className="page-heading">
        <h1>Study Plan</h1>
        <p>Loading personalised study plan...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-heading">
        <h1>Study Plan</h1>
        <p>{error}</p>
      </div>
    )
  }

  return (
    <div>
      <div className="page-heading">
        <h1>{studentName}&apos;s Study Plan</h1>
        <p>Your personalised study plan based on identified skill gaps</p>
      </div>

      {recommendations.length === 0 ? (
        <div className="empty-state">
          <p>No study plan recommendations available yet.</p>
        </div>
      ) : (
        <div className="study-plan-grid">
          {recommendations.map((item, index) => (
            <div
              className="study-plan-card"
              key={`${item.learning_report_id}-${index}`}
            >
              <h3>{item.title || `Study Focus ${index + 1}`}</h3>

              {item.course_name && (
                <p className="study-tip-course">
                  {item.course_name}
                </p>
              )}

              {item.related_area && (
                <p className="study-tip-subtitle">
                  {item.related_area}
                </p>
              )}

              <p>{item.action}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}