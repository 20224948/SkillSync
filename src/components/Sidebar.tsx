'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'

import { supabase } from '../app/lib/supabaseClient'

import {
  AdaptiveQuizSidebarIcon,
  DashboardSidebarIcon,
  SignOutSidebarIcon,
  StudyPlanSidebarIcon,
  StudyTipsSidebarIcon,
} from './SidebarIcons'

/*
|--------------------------------------------------------------------------
| Sidebar Navigation Configuration
|--------------------------------------------------------------------------
| Centralised navigation items used to render sidebar links.
| Makes it easier to maintain routes, labels, and icons in one place.
|--------------------------------------------------------------------------
*/

const navItems = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: DashboardSidebarIcon,
  },
  {
    label: 'Study Plan',
    href: '/study-plan',
    icon: StudyPlanSidebarIcon,
  },
  {
    label: 'Adaptive Quiz',
    href: '/adaptive-quiz',
    icon: AdaptiveQuizSidebarIcon,
  },
  {
    label: 'Study Tips',
    href: '/study-tips',
    icon: StudyTipsSidebarIcon,
  },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()

  /*
  |--------------------------------------------------------------------------
  | Logout Handler
  |--------------------------------------------------------------------------
  | Signs the user out through Supabase authentication,
  | then redirects them back to the landing/login page.
  |--------------------------------------------------------------------------
  */

  async function handleLogout() {
    await supabase.auth.signOut()

    router.push('/')
    router.refresh()
  }

  return (
    <aside className="sidebar">
      {/* SkillSync logo section */}
      <div className="sidebar-logo">
        <img
          src="/skillsync-logo.png"
          alt="SkillSync logo"
          className="sidebar-logo-image"
        />
      </div>

      {/* Main navigation links */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${isActive ? 'active' : ''}`}
            >
              <span className="sidebar-icon-wrap">
                <Icon size={52} />
              </span>

              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Pushes logout button to bottom of sidebar */}
      <div className="sidebar-spacer" />

      {/* Logout action */}
      <button
        type="button"
        className="sidebar-logout"
        onClick={handleLogout}
      >
        <span className="sidebar-icon-wrap">
          <SignOutSidebarIcon size={40} />
        </span>

        <span className="sidebar-logout-text">Logout</span>
      </button>
    </aside>
  )
}