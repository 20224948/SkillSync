'use client'

import { usePathname } from 'next/navigation'

import ProfileHeader from './ProfileHeader'
import Sidebar from './Sidebar'

type AppShellProps = {
  children: React.ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  const pathname = usePathname()

  // Login/auth pages should not use the dashboard sidebar layout.
  const isAuthPage = pathname === '/' || pathname === '/login'

  if (isAuthPage) {
    return <>{children}</>
  }

  return (
    <div className="app-shell">
      <Sidebar />

      <main className="app-main">
        <ProfileHeader />

        {/* Main page content is injected here for each route */}
        <div className="page-container">{children}</div>
      </main>
    </div>
  )
}