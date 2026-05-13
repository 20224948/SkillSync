import { ReactNode } from 'react'

type GradientCardProps = {
  children: ReactNode
  className?: string
}

export default function GradientCard({
  children,
  className = '',
}: GradientCardProps) {
  // Allows pages to reuse the shared gradient card style with optional extra classes.
  return <div className={`gradient-card ${className}`.trim()}>{children}</div>
}