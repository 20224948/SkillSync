// Import global styles (applies to entire application)
import './globals.css'

// Import shared layout components
import Sidebar from '../components/Sidebar'
import ProfileHeader from '../components/ProfileHeader'

// Metadata used by Next.js for SEO and browser tab info
export const metadata = {
  title: 'SkillSync',
  description: 'Learning analysis dashboard',
}

// RootLayout wraps ALL pages in the app (global layout)
// This is part of Next.js App Router architecture
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    // Root HTML structure (applies globally)
    <html lang="en">
      <body>
        {/* 
          App Shell:
          Defines the overall layout structure of the application.
          Consists of a sidebar for navigation and a main content area.
        */}
        <div className="app-shell">

          {/* Sidebar navigation (persistent across all pages) */}
          <Sidebar />

          {/* Main content area */}
          <main className="app-main">

            {/* 
              ProfileHeader:
              Displays user-related info (e.g. avatar, name, logout)
              Appears at the top of every page
            */}
            <ProfileHeader />

            {/* 
              Page Container:
              This is where individual page content is rendered.
              The `children` prop represents the current route's page.
            */}
            <div className="page-container">{children}</div>

          </main>
        </div>
      </body>
    </html>
  )
}