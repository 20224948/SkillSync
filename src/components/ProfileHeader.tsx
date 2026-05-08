'use client'

import { useEffect, useState } from 'react'
import { supabase } from '../app/lib/supabaseClient'

export default function ProfileHeader() {
  const [studentName, setStudentName] = useState('Student')

  useEffect(() => {
    async function loadStudent() {
      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session?.user) {
        setStudentName('Student')
        return
      }

      const { data } = await supabase
        .from('students')
        .select('display_name')
        .eq('auth_user_id', session.user.id)
        .maybeSingle()

      setStudentName(data?.display_name || 'Student')
    }

    loadStudent()

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      loadStudent()
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  const initials = studentName
    .split(' ')
    .map((word) => word[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div className="profile-header">
      <div className="profile-header-content">
        <span className="profile-name">{studentName}</span>
        <div className="profile-avatar">{initials}</div>
      </div>
    </div>
  )
}