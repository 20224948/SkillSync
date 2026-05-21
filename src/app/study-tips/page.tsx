'use client'

import { useEffect, useState } from 'react'
import { getStudyTipsData } from '../lib/api'

interface StudyTip {
  learning_report_id: string
  title: string
  related_area: string
  recommendation:
  | string
  | {
    title?: string
    action?: string
    reason?: string
    related_area?: string
  }
  action?: string
  course_name: string
}

export default function StudyTipsPage() {
  const [tips, setTips] = useState<StudyTip[]>([])
  const [studentName, setStudentName] = useState('Student')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadStudyTips() {
      try {
        setLoading(true)
        const data = await getStudyTipsData()

        setTips(data.tips ?? [])
        setStudentName(data.student?.display_name ?? 'Student')
      } catch (err: any) {
        console.error(err)
        setError(err.message || 'Failed to load study tips')
      } finally {
        setLoading(false)
      }
    }

    loadStudyTips()
  }, [])

  if (loading) {
    return (
      <div className="page-heading">
        <h1>Study Tips</h1>
        <p>Loading personalised study tips...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-heading">
        <h1>Study Tips</h1>
        <p>{error}</p>
      </div>
    )
  }

  return (
    <div>
      <div className="page-heading">
        <h1>{studentName}&apos;s Study Tips</h1>
        <p>Here are personalised study tips for {studentName}.</p>
      </div>

      {tips.length === 0 ? (
        <div className="empty-state">
          <p>No study tips available yet.</p>
        </div>
      ) : (
        <div className="study-tips-list">
          {tips.map((item, index) => (
            <div
              className="study-tip-row"
              key={`${item.learning_report_id}-${index}`}
            >
              <h3>{item.title || `Study Tip ${index + 1}`}</h3>

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

              <p>
                {typeof item.recommendation === 'string'
                  ? item.recommendation
                  : item.recommendation?.action ||
                  item.recommendation?.reason ||
                  item.action ||
                  'No recommendation text available.'}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}