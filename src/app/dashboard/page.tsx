'use client'

import { useEffect } from 'react'
import { getStudentData } from '../lib/api'

// DashboardPage component
// This is the main landing page after login, showing user learning analytics
export default function DashboardPage() {
  useEffect(() => {
    async function loadStudentData() {
      try {
        const data = await getStudentData()
        console.log('Dashboard API DATA:', data)
      } catch (error) {
        console.error('Failed to load dashboard data:', error)
      }
    }

    loadStudentData()
  }, [])

  return (
    <div>
      {/* Page header section */}
      <div className="page-heading">
        <h1>Welcome back!</h1>
        <p>Here is the current learning analysis.</p>
      </div>

      {/* Top grid section containing key summary cards */}
      <div className="dashboard-grid-top">
        {/* Overall Mastery Card */}
        <div className="soft-card">
          <h3 className="metric-title">Overall Mastery</h3>

          {/* Circular mastery indicator (currently empty state) */}
          <div className="mastery-wrap">
            <div className="mastery-ring empty">
              {/* Placeholder value until real data is connected */}
              <div className="mastery-ring-inner">--%</div>
            </div>
          </div>
        </div>

        {/* Strengths Card */}
        <div className="soft-card">
          <h3 className="metric-title">Strengths</h3>

          {/* Empty state when no strength data is available */}
          <div className="card-empty-body">
            <p>No strength data available</p>
          </div>
        </div>

        {/* Needs Improvement Card */}
        <div className="soft-card">
          <h3 className="metric-title">Needs Improvement</h3>

          {/* Empty state when no improvement data is available */}
          <div className="card-empty-body">
            <p>No improvement data available</p>
          </div>
        </div>
      </div>

      {/* Progress Over Time Chart Section */}
      <div className="soft-card progress-chart-card">
        <h3 className="metric-title">Progress Over Time</h3>

        {/* Placeholder for future chart integration */}
        <div className="card-empty-body chart-empty">
          <p>No progress data available</p>
        </div>
      </div>
    </div>
  )
}