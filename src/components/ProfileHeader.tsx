'use client'

import { useEffect, useState } from 'react'

import { supabase } from '../app/lib/supabaseClient'

export default function ProfileHeader() {
  // Stores the logged-in student's display name.
  const [studentName, setStudentName] = useState('Student')

  useEffect(() => {
    /*
    |--------------------------------------------------------------------------
    | Load Student Profile
    |--------------------------------------------------------------------------
    | Retrieves the current authenticated user's display name
    | from the students table in Supabase.
    |--------------------------------------------------------------------------
    */

    async function loadStudent() {
      const {
        data: { session },
      } = await supabase.auth.getSession()

      // Fallback state if no authenticated session exists.
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

    /*
    |--------------------------------------------------------------------------
    | Auth State Listener
    |--------------------------------------------------------------------------
    | Automatically refreshes profile information when the
    | authentication state changes.
    |--------------------------------------------------------------------------
    */

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      loadStudent()
    })

    // Cleanup listener on component unmount.
    return () => {
      subscription.unsubscribe()
    }
  }, [])

  /*
  |--------------------------------------------------------------------------
  | Avatar Initials Generator
  |--------------------------------------------------------------------------
  | Converts the student's name into profile initials.
  | Example: "Mark Prado" -> "MP"
  |--------------------------------------------------------------------------
  */

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