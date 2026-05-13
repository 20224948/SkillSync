'use client'

import { useEffect, useState } from 'react'

import { getStudentData } from '../lib/api'

export default function DashboardPage() {
  /*
  |--------------------------------------------------------------------------
  | Component State
  |--------------------------------------------------------------------------
  */

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reportData, setReportData] = useState<any>(null)

  /*
  |--------------------------------------------------------------------------
  | Load Dashboard Data
  |--------------------------------------------------------------------------
  | Retrieves the latest learning report, mastery scores,
  | and competency trend information for the logged-in student.
  |--------------------------------------------------------------------------
  */

  useEffect(() => {
    async function loadStudentData() {
      try {
        const data = await getStudentData()

        console.log('Dashboard API DATA:', data)

        setReportData(data)
      } catch (error: any) {
        console.error('Failed to load dashboard data:', error)

        setError(error?.message || 'Failed to load dashboard')
      } finally {
        setLoading(false)
      }
    }

    loadStudentData()
  }, [])

  /*
  |--------------------------------------------------------------------------
  | Loading / Error States
  |--------------------------------------------------------------------------
  */

  if (loading) return <p>Loading dashboard...</p>

  if (error) return <p>Error: {error}</p>

  /*
  |--------------------------------------------------------------------------
  | Dashboard Data Preparation
  |--------------------------------------------------------------------------
  */

  const report = reportData?.report

  const studentName =
    reportData?.student?.display_name ||
    report?.student?.name ||
    'Student'

  const overallMastery =
    reportData?.overall_mastery_score ??
    report?.mastery_report?.overall_mastery_score ??
    0

  /*
  |--------------------------------------------------------------------------
  | SILO / Competency Data
  |--------------------------------------------------------------------------
  | Uses normalized mastery rows when available, otherwise falls
  | back to report JSON data.
  |--------------------------------------------------------------------------
  */

  const silos =
    reportData?.masteryRows?.length > 0
      ? reportData.masteryRows
      : report?.mastery_report?.silo_mastery ?? []

  /*
  |--------------------------------------------------------------------------
  | Strength & Weak Area Calculations
  |--------------------------------------------------------------------------
  */

  const strengths = [...silos]
    .filter((item: any) => Number(item.mastery_score) >= 70)
    .sort(
      (a: any, b: any) =>
        Number(b.mastery_score) - Number(a.mastery_score)
    )
    .slice(0, 3)

  const weakAreas = [...silos]
    .sort(
      (a: any, b: any) =>
        Number(a.mastery_score) - Number(b.mastery_score)
    )
    .slice(0, 3)

  return (
    <div className="dashboard-page">
      {/* Page heading */}
      <div className="page-heading">
        <h1>Welcome back, {studentName.split(' ')[0]}!</h1>

        <p>Here is your current learning analysis:</p>
      </div>

      {/* Dashboard summary cards */}
      <div className="dashboard-grid-top">
        {/* Overall mastery card */}
        <div className="soft-card dashboard-card">
          <h3 className="metric-title">Overall Mastery</h3>

          <div className="mastery-wrap">
            <div
              className="mastery-ring"
              style={
                {
                  '--percentage': Number(overallMastery),
                } as React.CSSProperties
              }
            >
              <div className="mastery-ring-inner">
                {Number(overallMastery).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>

        {/* Strengths card */}
        <div className="soft-card dashboard-card">
          <h3 className="metric-title">Strengths</h3>

          <div className="dashboard-list">
            {strengths.length === 0 ? (
              <p>No strength data available</p>
            ) : (
              strengths.map((item: any, index: number) => (
                <div className="dashboard-list-row" key={index}>
                  <span>{cleanTitle(item.title)}</span>

                  <div className="dashboard-progress">
                    <div
                      className="dashboard-progress-fill"
                      style={{
                        width: `${Number(item.mastery_score)}%`,
                      }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Weak areas card */}
        <div className="soft-card dashboard-card">
          <h3 className="metric-title">Needs Improvement</h3>

          <div className="dashboard-list">
            {weakAreas.length === 0 ? (
              <p>No improvement data available</p>
            ) : (
              weakAreas.map((item: any, index: number) => (
                <div className="dashboard-list-row" key={index}>
                  <span>{cleanTitle(item.title)}</span>

                  <div className="dashboard-progress">
                    <div
                      className="dashboard-progress-fill weak"
                      style={{
                        width: `${Number(item.mastery_score)}%`,
                      }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Detailed competency overview */}
      <div className="soft-card learning-overview-card">
        <h3 className="metric-title">
          Current Learning Overview
        </h3>

        <div className="learning-overview-list">
          {silos.length === 0 ? (
            <p>No learning overview data available</p>
          ) : (
            silos.map((silo: any, index: number) => (
              <div
                className="learning-overview-item"
                key={index}
              >
                <span className="learning-overview-title">
                  {silo.competency_id} -{' '}
                  {cleanTitle(silo.title)}
                </span>

                <div className="dashboard-progress">
                  <div
                    className="dashboard-progress-fill"
                    style={{
                      width: `${Number(silo.mastery_score)}%`,
                    }}
                  />
                </div>

                <span className="learning-overview-score">
                  {silo.previous_mastery_score !== null &&
                  silo.previous_mastery_score !== undefined ? (
                    <span
                      className={
                        Number(silo.mastery_change) >= 0
                          ? 'trend-positive'
                          : 'trend-negative'
                      }
                    >
                      {Number(
                        silo.previous_mastery_score
                      ).toFixed(0)}
                      % →{' '}
                      {Number(silo.mastery_score).toFixed(0)}% (
                      {Number(silo.mastery_change) >= 0
                        ? '+'
                        : ''}
                      {Number(silo.mastery_change).toFixed(0)}
                      %)
                    </span>
                  ) : (
                    <span>
                      {Number(silo.mastery_score).toFixed(0)}%
                    </span>
                  )}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

/*
|--------------------------------------------------------------------------
| Utility: Clean SILO Title
|--------------------------------------------------------------------------
| Removes redundant SILO prefixes to improve UI readability.
|--------------------------------------------------------------------------
*/

function cleanTitle(title: string) {
  return title
    ?.replace(/^SILO\s*\d+\s*-\s*/i, '')
    ?.replace(/\s+/g, ' ')
    ?.trim()
}