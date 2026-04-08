type IconProps = {
  size?: number
}

export function DashboardSidebarIcon({ size = 40 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      <defs>
        <linearGradient id="dashboardGradient" x1="4" y1="4" x2="36" y2="36" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#DF40FF" />
          <stop offset="50%" stopColor="#6F63FF" />
          <stop offset="100%" stopColor="#3EA6FF" />
        </linearGradient>
      </defs>

      <rect x="6" y="6" width="12" height="12" rx="2.5" fill="url(#dashboardGradient)" />
      <rect x="22" y="6" width="12" height="12" rx="2.5" fill="url(#dashboardGradient)" />
      <rect x="6" y="22" width="12" height="12" rx="2.5" fill="url(#dashboardGradient)" />
      <rect x="22" y="22" width="12" height="12" rx="2.5" fill="url(#dashboardGradient)" />
    </svg>
  )
}

export function StudyPlanSidebarIcon({ size = 40 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      <defs>
        <linearGradient id="studyPlanGradient" x1="4" y1="4" x2="36" y2="36" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#DF40FF" />
          <stop offset="50%" stopColor="#6F63FF" />
          <stop offset="100%" stopColor="#3EA6FF" />
        </linearGradient>
      </defs>

      <path
        d="M20 6L34 13L20 20L6 13L20 6ZM11 17.5V22.5C11 25.8 15.1 28.5 20 28.5C24.9 28.5 29 25.8 29 22.5V17.5L20 22L11 17.5Z"
        fill="url(#studyPlanGradient)"
      />
    </svg>
  )
}

export function AdaptiveQuizSidebarIcon({ size = 40 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      <defs>
        <linearGradient id="adaptiveQuizGradient" x1="4" y1="4" x2="36" y2="36" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#DF40FF" />
          <stop offset="50%" stopColor="#6F63FF" />
          <stop offset="100%" stopColor="#3EA6FF" />
        </linearGradient>
      </defs>

      <rect x="7" y="8" width="18" height="24" rx="4" fill="url(#adaptiveQuizGradient)" />
      <circle cx="12" cy="14" r="1.7" fill="white" />
      <rect x="15" y="13" width="7" height="2" rx="1" fill="white" />
      <rect x="11" y="18" width="11" height="2" rx="1" fill="white" />
      <rect x="11" y="23" width="8" height="2" rx="1" fill="white" />
      <circle cx="28" cy="27" r="7" fill="url(#adaptiveQuizGradient)" />
      <path d="M28 23V31" stroke="white" strokeWidth="2" strokeLinecap="round" />
      <path d="M24 27H32" stroke="white" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function StudyTipsSidebarIcon({ size = 40 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      <defs>
        <linearGradient id="studyTipsGradient" x1="4" y1="4" x2="36" y2="36" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#DF40FF" />
          <stop offset="50%" stopColor="#6F63FF" />
          <stop offset="100%" stopColor="#3EA6FF" />
        </linearGradient>
      </defs>

      <path
        d="M20 7C14.8 7 10.8 10.9 10.8 15.8C10.8 19 12.4 21.3 14.5 23.2C15.7 24.3 16.3 25.2 16.6 26.4H23.4C23.7 25.2 24.3 24.3 25.5 23.2C27.6 21.3 29.2 19 29.2 15.8C29.2 10.9 25.2 7 20 7Z"
        fill="url(#studyTipsGradient)"
      />
      <rect x="16.4" y="27.5" width="7.2" height="2.3" rx="1.15" fill="url(#studyTipsGradient)" />
      <rect x="17.2" y="30.8" width="5.6" height="2.1" rx="1.05" fill="url(#studyTipsGradient)" />
      <path d="M20 12V17" stroke="white" strokeWidth="2" strokeLinecap="round" />
      <circle cx="20" cy="20.3" r="1.2" fill="white" />
      <path d="M12.5 16H15" stroke="url(#studyTipsGradient)" strokeWidth="2" strokeLinecap="round" />
      <path d="M25 16H27.5" stroke="url(#studyTipsGradient)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function SignOutSidebarIcon({
  size = 24,
}: {
  size?: number
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
    >
      <defs>
        <linearGradient
          id="signOutGradient"
          x1="0"
          y1="0"
          x2="24"
          y2="24"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor="#DF40FF" />
          <stop offset="50%" stopColor="#6F63FF" />
          <stop offset="100%" stopColor="#3EA6FF" />
        </linearGradient>
      </defs>

      <path
        d="M16 17L21 12L16 7"
        stroke="url(#signOutGradient)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M21 12H9"
        stroke="url(#signOutGradient)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M13 21H5C4.44772 21 4 20.5523 4 20V4C4 3.44772 4.44772 3 5 3H13"
        stroke="url(#signOutGradient)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}