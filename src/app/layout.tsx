import './globals.css'
import AppShell from '../components/AppShell'

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
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}