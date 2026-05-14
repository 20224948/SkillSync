'use client'

// Handles automatic logout after user inactivity

import { useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../app/lib/supabaseClient'

// Inactivity timeout duration
const TIMEOUT_MINUTES = 20
const TIMEOUT_MS = TIMEOUT_MINUTES * 60 * 1000

export default function SessionTimeout() {

    // Used for redirecting users after logout
    const router = useRouter()

    // Stores the current timeout instance
    const timeoutRef = useRef<NodeJS.Timeout | null>(null)

    useEffect(() => {

        // Resets the inactivity timer whenever activity is detected
        const resetTimer = () => {

            // Clear the existing timeout before creating a new one
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current)
            }

            // Start inactivity countdown
            timeoutRef.current = setTimeout(async () => {

                // Check if a valid session still exists
                const { data } = await supabase.auth.getSession()

                // Sign the user out if logged in
                if (data.session) {
                    await supabase.auth.signOut()
                }

                // Redirect back to landing/login page
                router.push('/')

            }, TIMEOUT_MS)
        }

        // Browser events treated as user activity
        const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart']

        // Attach activity listeners
        events.forEach((event) => {
            window.addEventListener(event, resetTimer)
        })

        // Start timer immediately on page load
        resetTimer()

        // Cleanup listeners and timers when component unmounts
        return () => {

            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current)
            }

            events.forEach((event) => {
                window.removeEventListener(event, resetTimer)
            })
        }

    }, [router])

    // No visible UI rendered
    return null
}