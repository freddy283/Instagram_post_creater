'use client'
import { Suspense, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { instagramApi, isAuthenticated } from '@/lib/api'

function IgIcon({ size = 24, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
    </svg>
  )
}

// Inner component uses useSearchParams — must be inside Suspense
function ConnectInstagramInner() {
  const router = useRouter()
  const sp = useSearchParams()
  const qc = useQueryClient()

  useEffect(() => {
    if (!isAuthenticated()) router.push('/auth/login')
    if (sp.get('ig_connected')) qc.invalidateQueries({ queryKey: ['ig-status'] })
  }, [])

  const { data: igStatus, isLoading } = useQuery({
    queryKey: ['ig-status'],
    queryFn: () => instagramApi.status().catch(() => null),
  })

  const connectMut = useMutation({
    mutationFn: async () => {
      const data = await instagramApi.authUrl()
      window.location.href = data.auth_url
    },
  })

  const disconnectMut = useMutation({
    mutationFn: () => instagramApi.disconnect(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ig-status'] }),
  })

  const connected = igStatus?.status === 'connected'
  const needsSetup = igStatus?.status === 'not_configured'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}
      className="flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        <Link href="/dashboard" className="flex items-center gap-2 text-sm"
          style={{ color: 'var(--text-2)', textDecoration: 'none' }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>arrow_back</span>
          Back to Dashboard
        </Link>

        <div className="text-center space-y-3">
          <IgIcon size={48} color="var(--gold)" />
          <h1 className="serif text-3xl">Connect Instagram</h1>
          <p style={{ color: 'var(--text-2)', fontSize: 15, lineHeight: 1.6 }}>
            This is <strong>optional</strong> — Aureus generates your videos regardless.
            Connect only if you want automatic daily posting.
          </p>
        </div>

        {isLoading ? (
          <div className="text-center" style={{ color: 'var(--text-muted)' }}>Checking status…</div>
        ) : connected ? (
          <div className="glass rounded-2xl p-6 space-y-4">
            <div className="flex items-center gap-3 p-4 rounded-xl"
              style={{ background: 'rgba(34,197,94,.08)', border: '1px solid rgba(34,197,94,.2)' }}>
              <span className="material-symbols-outlined" style={{ color: '#4ade80', fontSize: 24 }}>check_circle</span>
              <div>
                <div className="font-bold" style={{ color: 'var(--text)' }}>Account Connected</div>
                <div className="text-sm" style={{ color: 'var(--text-2)' }}>@{igStatus?.connection?.ig_username}</div>
              </div>
            </div>
            <p className="text-sm" style={{ color: 'var(--text-2)' }}>
              Aureus will post your daily video as a Reel at your scheduled time, automatically.
            </p>
            <Link href="/dashboard" className="btn btn-gold rounded-xl px-6 py-3.5 text-sm font-bold w-full"
              style={{ textDecoration: 'none' }}>
              Back to Dashboard
            </Link>
            <button onClick={() => disconnectMut.mutate()} disabled={disconnectMut.isPending}
              className="btn btn-ghost rounded-xl px-6 py-3 text-sm w-full" style={{ color: '#f87171' }}>
              Disconnect Account
            </button>
          </div>
        ) : needsSetup ? (
          <div className="glass rounded-2xl p-6 space-y-4">
            <div className="flex items-center gap-3 p-4 rounded-xl"
              style={{ background: 'rgba(251,191,36,.08)', border: '1px solid rgba(251,191,36,.2)' }}>
              <span className="material-symbols-outlined" style={{ color: '#fbbf24', fontSize: 24 }}>warning</span>
              <div className="text-sm" style={{ color: 'var(--text-2)' }}>
                Instagram API not configured. Add <code style={{ color: 'var(--gold)' }}>INSTAGRAM_APP_ID</code> and{' '}
                <code style={{ color: 'var(--gold)' }}>INSTAGRAM_APP_SECRET</code> to backend .env.
              </div>
            </div>
            <Link href="/dashboard" className="btn btn-outline rounded-xl px-6 py-3.5 text-sm font-bold w-full"
              style={{ textDecoration: 'none' }}>
              Continue without Instagram
            </Link>
          </div>
        ) : (
          <div className="glass rounded-2xl p-6 space-y-5">
            <button onClick={() => connectMut.mutate()} disabled={connectMut.isPending}
              className="btn btn-gold rounded-xl px-6 py-4 text-base font-bold w-full">
              <IgIcon size={22} />
              {connectMut.isPending ? 'Redirecting…' : 'Continue with Instagram'}
            </button>

            <div className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-widest" style={{ color: 'var(--text-2)' }}>What happens next</p>
              {[
                ['login', 'Instagram opens in your browser'],
                ['check_circle', 'You approve posting permission'],
                ['movie_filter', 'Aureus posts your daily video as a Reel'],
              ].map(([icon, text]) => (
                <div key={text} className="flex items-center gap-3">
                  <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--gold)' }}>{icon}</span>
                  <span className="text-sm" style={{ color: 'var(--text-2)' }}>{text}</span>
                </div>
              ))}
            </div>

            <div className="text-xs p-3 rounded-lg" style={{ background: 'var(--card-hover)', color: 'var(--text-muted)' }}>
              Requires an Instagram Business or Creator account.{' '}
              <a href="https://help.instagram.com/502981923235522" target="_blank" rel="noopener noreferrer"
                style={{ color: 'var(--gold)' }}>How to switch →</a>
              <br />We never see or store your Instagram password.
            </div>

            <Link href="/dashboard" className="btn btn-ghost rounded-xl px-6 py-3 text-sm w-full"
              style={{ textDecoration: 'none', color: 'var(--text-2)' }}>
              Skip — I&apos;ll post manually
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}

// Outer component wraps inner in Suspense — required for useSearchParams in Next.js 15
export default function ConnectInstagram() {
  return (
    <Suspense fallback={
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-muted)' }}>Loading…</div>
      </div>
    }>
      <ConnectInstagramInner />
    </Suspense>
  )
}
