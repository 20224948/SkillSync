import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="home-redirect">
      <h1>SkillSync</h1>
      <p>Student learning insights and personalised academic support.</p>
      <p>This interface is currently using static layout placeholders while integration is in progress.</p>

      <div className="home-actions">
        <Link href="/dashboard" className="home-link-btn">
          View Dashboard Layout
        </Link>
      </div>
    </div>
  )
}