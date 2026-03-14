'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { authApi, isAuthenticated } from '@/lib/api'
import { useTheme } from '@/lib/theme'
import { useEffect } from 'react'

function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button onClick={toggle} className="theme-toggle">
      <span style={{ fontSize: 14 }}>{theme === 'dark' ? '☀️' : '🌙'}</span>
      <div className={`toggle-track ${theme === 'light' ? 'on' : ''}`}><div className="toggle-thumb" /></div>
    </button>
  )
}

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated()) router.push('/dashboard')
  }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) { setError('Please fill in all fields'); return }
    setLoading(true); setError('')
    try {
      await authApi.login(email, password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}
      className="flex flex-col items-center justify-center px-4">

      {/* Top nav */}
      <div className="fixed top-0 w-full flex items-center justify-between px-6 py-4"
        style={{ borderBottom: '1px solid var(--border-light)', background: 'var(--nav-bg)' }}>
        <Link href="/" className="flex items-center gap-2" style={{ textDecoration: 'none' }}>
          <span className="material-symbols-outlined" style={{ color: 'var(--gold)', fontSize: 22 }}>movie_filter</span>
          <span className="font-bold tracking-wide text-base" style={{ color: 'var(--text)' }}>Aureus</span>
        </Link>
        <ThemeToggle />
      </div>

      <div className="w-full max-w-sm space-y-8 pt-16">
        <div className="text-center">
          <h1 className="serif text-4xl mb-2">Welcome back</h1>
          <p style={{ color: 'var(--text-2)', fontSize: 15 }}>Sign in to your Aureus account</p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          {error && (
            <div className="p-4 rounded-xl text-sm" style={{ background: 'rgba(239,68,68,.1)', color: '#f87171', border: '1px solid rgba(239,68,68,.2)' }}>
              {error}
            </div>
          )}
          <div>
            <label className="block text-xs font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-2)' }}>Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              className="inp" placeholder="you@example.com" autoComplete="email" />
          </div>
          <div>
            <label className="block text-xs font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-2)' }}>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="inp" placeholder="••••••••" autoComplete="current-password" />
          </div>
          <button type="submit" disabled={loading}
            className="btn btn-gold rounded-xl px-6 py-4 text-sm font-bold w-full mt-2">
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-sm" style={{ color: 'var(--text-2)' }}>
          Don&apos;t have an account?{' '}
          <Link href="/auth/register" style={{ color: 'var(--gold)', textDecoration: 'none', fontWeight: 600 }}>
            Create one free
          </Link>
        </p>
      </div>
    </div>
  )
}
