import './globals.css'
import AppShell from '../components/AppShell'
import SessionTimeout from '../components/SessionTimeout'

export const metadata = {
  title: 'SkillSync',
  description: 'Learning analysis dashboard',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body>
        {/* Automatically signs out inactive users */}
        <SessionTimeout />

        {/* AppShell controls the shared layout shown after login */}
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}