'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { supabase } from './lib/supabaseClient'

export default function LoginPage() {
  const router = useRouter()

  // Form state used for Supabase authentication.
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  // UI feedback state for login errors and loading status.
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()

    setLoading(true)
    setError('')

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    // Successful login redirects the student to the dashboard.
    router.push('/dashboard')
  }

  return (
    <div className="login-page">
      {/* Decorative background glow for the login screen */}
      <div className="login-background-glow" />

      <div className="login-card">
        <img
          src="/skillsync-logo.png"
          alt="SkillSync Logo"
          className="login-logo"
        />

        <h1>Welcome Back</h1>

        <p className="login-subtitle">
          Personalised learning insights powered by adaptive analysis.
        </p>

        <form onSubmit={handleLogin} className="login-form">
          <input
            type="email"
            placeholder="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {error && <p className="login-error">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}