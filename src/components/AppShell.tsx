'use client'

import { usePathname } from 'next/navigation'
import Sidebar from './Sidebar'
import ProfileHeader from './ProfileHeader'

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  const isAuthPage = pathname === '/' || pathname === '/login'

  if (isAuthPage) {
    return <>{children}</>
  }

  return (
    <div className="app-shell">
      <Sidebar />

      <main className="app-main">
        <ProfileHeader />
        <div className="page-container">{children}</div>
      </main>
    </div>
  )
}