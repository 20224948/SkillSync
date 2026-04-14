'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  DashboardSidebarIcon,
  StudyPlanSidebarIcon,
  AdaptiveQuizSidebarIcon,
  StudyTipsSidebarIcon,
  SignOutSidebarIcon,
} from './SidebarIcons'

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

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img
          src="/skillsync-logo.png"
          alt="SkillSync logo"
          className="sidebar-logo-image"
        />
      </div>

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

      <div className="sidebar-spacer" />

      <Link href="/" className="sidebar-logout">
  <span className="sidebar-icon-wrap">
    <SignOutSidebarIcon size={40} />
  </span>
  <span className="sidebar-logout-text">Logout</span>
</Link>
    </aside>
  )
}