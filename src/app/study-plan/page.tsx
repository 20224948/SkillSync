'use client'

import { useEffect } from 'react'
import { getStudentData } from '../lib/api'

export default function StudyPlanPage() {
  useEffect(() => {
    async function loadStudentData() {
      try {
        const data = await getStudentData()
        console.log('Study Plan API DATA:', data)
      } catch (error) {
        console.error('Failed to load study plan data:', error)
      }
    }

    loadStudentData()
  }, [])

  return (
    <div>
      <div className="page-heading">
        <h1>Study Plan</h1>
        <p>A personalised study plan will appear here once learning data is available.</p>
      </div>

      <div className="empty-state">
        <p>No study plan generated yet</p>
      </div>
    </div>
  )
}