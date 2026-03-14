'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { authApi, isAuthenticated } from '@/lib/api'
import { useTheme } from '@/lib/theme'

function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button onClick={toggle} className="theme-toggle">
      <span style={{ fontSize: 14 }}>{theme === 'dark' ? '☀️' : '🌙'}</span>
      <div className={`toggle-track ${theme === 'light' ? 'on' : ''}`}><div className="toggle-thumb" /></div>
    </button>
  )
}

const TZ = ['UTC','America/New_York','America/Chicago','America/Los_Angeles',
  'Europe/London','Europe/Berlin','Asia/Kolkata','Asia/Dubai','Asia/Tokyo','Asia/Singapore']

export default function RegisterPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [tz, setTz] = useState('UTC')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated()) router.push('/dashboard')
    // Auto-detect timezone
    try { setTz(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC') } catch {}
  }, [])

  const strength = !password ? 0 : password.length < 6 ? 1 : password.length < 10 ? 2 : 3
  const strengthLabel = ['', 'Weak', 'Fair', 'Strong'][strength]
  const strengthColor = ['', '#f87171', '#fbbf24', '#4ade80'][strength]

  const next = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name || !email) { setError('Please fill all fields'); return }
    if (!/\S+@\S+\.\S+/.test(email)) { setError('Enter a valid email'); return }
    setError(''); setStep(2)
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password) { setError('Enter a password'); return }
    if (password.length < 6) { setError('Password must be at least 6 characters'); return }
    if (password !== confirm) { setError('Passwords do not match'); return }
    setLoading(true); setError('')
    try {
      await authApi.register({ name, email, password, timezone: tz })
      await authApi.login(email, password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Registration failed')
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}
      className="flex flex-col items-center justify-center px-4">

      <div className="fixed top-0 w-full flex items-center justify-between px-6 py-4"
        style={{ borderBottom: '1px solid var(--border-light)', background: 'var(--nav-bg)' }}>
        <Link href="/" className="flex items-center gap-2" style={{ textDecoration: 'none' }}>
          <span className="material-symbols-outlined" style={{ color: 'var(--gold)', fontSize: 22 }}>movie_filter</span>
          <span className="font-bold tracking-wide text-base" style={{ color: 'var(--text)' }}>Aureus</span>
        </Link>
        <ThemeToggle />
      </div>

      <div className="w-full max-w-sm space-y-8 pt-16">
        {/* Progress */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs" style={{ color: 'var(--text-2)' }}>
            <span>Step {step} of 2</span>
            <span>{step === 1 ? 'Your details' : 'Create password'}</span>
          </div>
          <div className="rounded-full h-1 overflow-hidden" style={{ background: 'var(--border)' }}>
            <div className="h-full rounded-full transition-all duration-500"
              style={{ background: 'var(--gold)', width: step === 1 ? '50%' : '100%' }} />
          </div>
        </div>

        <div className="text-center">
          <h1 className="serif text-4xl mb-2">Create Account</h1>
          <p style={{ color: 'var(--text-2)', fontSize: 15 }}>Start generating your daily videos</p>
        </div>

        {error && (
          <div className="p-4 rounded-xl text-sm" style={{ background: 'rgba(239,68,68,.1)', color: '#f87171', border: '1px solid rgba(239,68,68,.2)' }}>
            {error}
          </div>
        )}

        {step === 1 ? (
          <form onSubmit={next} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-2)' }}>Name</label>
              <input value={name} onChange={e => setName(e.target.value)} className="inp" placeholder="Your name" autoFocus />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-2)' }}>Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="inp" placeholder="you@example.com" autoComplete="email" />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-2)' }}>Timezone</label>
              <select value={tz} onChange={e => setTz(e.target.value)} className="inp">
                {TZ.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <button type="submit" className="btn btn-gold rounded-xl px-6 py-4 text-sm font-bold w-full mt-2">
              Continue →
            </button>
          </form>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-2)' }}>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                className="inp" placeholder="Min 6 characters" autoFocus />
              {password && (
                <div className="mt-2 space-y-1">
                  <div className="rounded-full h-1 overflow-hidden" style={{ background: 'var(--border)' }}>
                    <div className="h-full rounded-full transition-all"
                      style={{ background: strengthColor, width: `${strength * 33}%` }} />
                  </div>
                  <p className="text-xs" style={{ color: strengthColor }}>{strengthLabel}</p>
                </div>
              )}
            </div>
            <div>
              <label className="block text-xs font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-2)' }}>Confirm Password</label>
              <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)}
                className={`inp ${confirm && confirm !== password ? 'error' : ''}`}
                placeholder="Repeat password" />
            </div>
            <div className="flex gap-3 mt-2">
              <button type="button" onClick={() => setStep(1)}
                className="btn btn-outline rounded-xl px-5 py-4 text-sm flex-shrink-0">
                ← Back
              </button>
              <button type="submit" disabled={loading}
                className="btn btn-gold rounded-xl px-6 py-4 text-sm font-bold flex-1">
                {loading ? 'Creating…' : 'Create Account'}
              </button>
            </div>
          </form>
        )}

        <p className="text-center text-sm" style={{ color: 'var(--text-2)' }}>
          Already have an account?{' '}
          <Link href="/auth/login" style={{ color: 'var(--gold)', textDecoration: 'none', fontWeight: 600 }}>
            Log in
          </Link>
        </p>
      </div>
    </div>
  )
}
