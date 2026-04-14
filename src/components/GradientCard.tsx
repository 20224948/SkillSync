import { ReactNode } from 'react'

type GradientCardProps = {
  children: ReactNode
  className?: string
}

export default function GradientCard({
  children,
  className = '',
}: GradientCardProps) {
  return <div className={`gradient-card ${className}`.trim()}>{children}</div>
}