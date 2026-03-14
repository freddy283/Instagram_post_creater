'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { isAuthenticated, userApi, videoApi, postsApi, scheduleApi, instagramApi, authApi } from '@/lib/api'
import { useTheme } from '@/lib/theme'
import { format } from 'date-fns'

type Tab = 'today' | 'history' | 'schedule' | 'settings'

const STATUS_LABEL: Record<string, string> = {
  success: 'Posted', failed: 'Failed', video_ready: 'Ready',
  pending: 'Pending', queued: 'Generating', skipped: 'Skipped',
}

function IgIcon({ size = 20, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
    </svg>
  )
}

function PageLoader({ message = 'Loading…' }: { message?: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 320, gap: 16 }}>
      <div style={{ width: 48, height: 48, borderRadius: '50%', border: '3px solid var(--dash-border)', borderTopColor: 'var(--gold)', animation: 'dashSpin 0.8s linear infinite' }} />
      <p style={{ color: 'var(--dash-muted)', fontSize: 14 }}>{message}</p>
    </div>
  )
}

function Spinner({ size = 18 }: { size?: number }) {
  return (
    <span style={{ display: 'inline-block', width: size, height: size, borderRadius: '50%', border: '2px solid rgba(128,128,128,0.3)', borderTopColor: 'currentColor', animation: 'dashSpin 0.7s linear infinite', flexShrink: 0 }} />
  )
}

// ── Generating banner — fully theme-aware ────────────────────────────────────
function GeneratingBanner({ realProgress }: { realProgress: number }) {
  const [fakeP, setFakeP] = useState(5)

  useEffect(() => {
    if (realProgress === 100) return
    const t = setInterval(() => {
      setFakeP(p => {
        // Slow down as we approach 90, never go past it until real completion
        const cap = realProgress > 0 ? Math.min(realProgress - 2, 90) : 90
        if (p >= cap) return p
        const step = p < 40 ? 1.8 : p < 70 ? 0.9 : 0.3
        return Math.min(p + step, cap)
      })
    }, 800)
    return () => clearInterval(t)
  }, [realProgress])

  const displayP = realProgress === 100 ? 100 : fakeP

  return (
    <div className="gen-banner">
      <div style={{ fontSize: 36, marginBottom: 12 }}>🎬</div>
      <div className="gen-banner-title">Generating your video…</div>
      <div className="gen-banner-sub">
        AI is writing the script, generating visuals,<br />
        and encoding with cinematic audio. ~30–90 seconds.
      </div>
      <div style={{ height: 8, background: 'var(--dash-card-2)', borderRadius: 8, overflow: 'hidden', marginBottom: 10 }}>
        <div style={{
          height: '100%', borderRadius: 8,
          background: 'linear-gradient(90deg, var(--gold), #f5d060)',
          width: `${displayP}%`,
          transition: displayP === 100 ? 'width 0.5s ease' : 'width 1.2s ease',
          boxShadow: '0 0 12px rgba(212,175,55,0.45)',
        }} />
      </div>
      <div className="gen-banner-pct">
        {displayP < 100 ? `${Math.round(displayP)}% complete — please keep this tab open` : '✓ Done!'}
      </div>
    </div>
  )
}

// ── Theme Toggle ─────────────────────────────────────────────────────────────
function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button onClick={toggle} className="theme-toggle">
      <span style={{ fontSize: 13 }}>{theme === 'dark' ? '☀️' : '🌙'}</span>
      <div className={`toggle-track ${theme === 'light' ? 'on' : ''}`}><div className="toggle-thumb" /></div>
    </button>
  )
}

// ── Sidebar ──────────────────────────────────────────────────────────────────
function Sidebar({ tab, setTab, user }: { tab: Tab; setTab: (t: Tab) => void; user: any }) {
  const NAV: [Tab, string, string][] = [
    ['today',    "Today's Video",  'video_camera_front'],
    ['history',  'Post History',   'history'],
    ['schedule', 'Schedule',       'calendar_month'],
    ['settings', 'Settings',       'settings'],
  ]
  return (
    <aside className="sidebar">
      <div style={{ borderBottom: '1px solid var(--sidebar-border)', padding: '20px' }} className="flex items-center gap-3">
        <span className="material-symbols-outlined" style={{ color: 'var(--gold)', fontSize: 26 }}>movie_filter</span>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: '.03em', color: 'var(--dash-text)', lineHeight: 1.2 }}>Aureus</div>
          <div style={{ fontSize: 11, color: 'var(--dash-muted)' }}>Video Automation</div>
        </div>
      </div>

      <nav style={{ flex: 1, padding: '12px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV.map(([id, label, icon]) => (
          <button key={id} onClick={() => setTab(id)} className={`nav-item${tab === id ? ' active' : ''}`}>
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>{icon}</span>
            {label}
          </button>
        ))}
      </nav>

      <div style={{ borderTop: '1px solid var(--sidebar-border)', padding: '12px' }}>
        <div style={{ marginBottom: 10 }}><ThemeToggle /></div>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 10, background: 'var(--dash-card-2)' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', flexShrink: 0, background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 13 }}>
              {user.name?.[0]?.toUpperCase()}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--dash-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.name}</div>
              <div style={{ fontSize: 11, color: 'var(--dash-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.email}</div>
            </div>
          </div>
        )}
        <button onClick={() => authApi.logout()} className="nav-item" style={{ color: '#f87171', marginTop: 4 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>logout</span>
          Log out
        </button>
      </div>
    </aside>
  )
}

// ── TODAY'S VIDEO TAB ────────────────────────────────────────────────────────
function TodayTab({ user }: { user: any }) {
  const qc = useQueryClient()
  const [poll, setPoll] = useState(false)
  const [realProgress, setRealProgress] = useState(0)

  const { data: statusData, isLoading: statusLoading } = useQuery({
    queryKey: ['video-status'],
    queryFn: () => videoApi.status(),
    refetchInterval: poll ? 2000 : false,   // faster 2s polling
  })

  const { data: igStatus } = useQuery({
    queryKey: ['ig-status'],
    queryFn: () => instagramApi.status().catch(() => null),
  })

  const generateMut = useMutation({
    mutationFn: () => videoApi.generate(),
    onSuccess: () => { setPoll(true); setRealProgress(5); qc.invalidateQueries({ queryKey: ['video-status'] }) },
  })

  useEffect(() => {
    const s = statusData?.status
    if (s === 'ready') {
      setRealProgress(100)
      setTimeout(() => { setPoll(false); qc.invalidateQueries({ queryKey: ['video-status'] }) }, 800)
    }
    if (s === 'error') {
      setPoll(false)
      setRealProgress(0)
    }
    // Bump fake progress landmarks based on backend stage hints
    if (s === 'generating' && statusData?.stage) {
      const stageMap: Record<string, number> = { script: 15, tts: 35, frames: 55, encoding: 80 }
      const p = stageMap[statusData.stage]
      if (p) setRealProgress(p)
    }
  }, [statusData?.status, statusData?.stage])

  if (statusLoading) return <PageLoader message="Loading video status…" />

  const status = statusData?.status ?? 'idle'
  const isGenerating = status === 'generating' || generateMut.isPending
  const hasVideo = statusData?.has_video
  const igConnected = igStatus?.status === 'connected'

  const cardStyle = { background: 'var(--dash-card)', border: '1px solid var(--dash-border)', borderRadius: 16, padding: 24 }

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {isGenerating && <GeneratingBanner realProgress={realProgress} />}

      {!isGenerating && (
        <div style={cardStyle}>
          <div style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4, color: 'var(--dash-text)' }}>Today&apos;s Video</h2>
            <p style={{ fontSize: 14, color: 'var(--dash-muted)', lineHeight: 1.6 }}>
              {hasVideo
                ? 'Your video is ready. Download it and post, or connect Instagram to auto-publish.'
                : 'Click below to generate a fresh AI-written motivational video for today.'}
            </p>
          </div>

          {status === 'error' && (
            <div style={{ background: 'rgba(239,68,68,.08)', color: '#f87171', border: '1px solid rgba(239,68,68,.2)', borderRadius: 10, padding: '10px 14px', fontSize: 13, marginBottom: 12 }}>
              ⚠ Generation failed. Check backend logs, then try again.
            </div>
          )}

          <button onClick={() => generateMut.mutate()} disabled={generateMut.isPending}
            className="btn btn-gold rounded-xl" style={{ width: '100%', height: 48, fontSize: 14, fontWeight: 700, gap: 8 }}>
            {generateMut.isPending
              ? <><Spinner size={16} /> Starting…</>
              : <><span className="material-symbols-outlined" style={{ fontSize: 20 }}>{hasVideo ? 'refresh' : 'movie_creation'}</span>{hasVideo ? 'Generate Fresh Video' : "Generate Today's Video"}</>
            }
          </button>
        </div>
      )}

      {/* Script/topic display */}
      {statusData?.topic && !isGenerating && (
        <div style={cardStyle}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 8 }}>Today&apos;s Topic</div>
          <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--dash-text)', marginBottom: 6 }}>{statusData.topic}</p>
          {statusData.quote && (
            <p className="serif" style={{ fontSize: 17, fontStyle: 'italic', lineHeight: 1.6, color: 'var(--dash-text)', marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--dash-border)' }}>
              &ldquo;{statusData.quote}&rdquo;
            </p>
          )}
          {statusData.author && <p style={{ marginTop: 6, fontSize: 13, color: 'var(--dash-muted)' }}>— {statusData.author}</p>}
        </div>
      )}

      {/* Quote (when no topic) */}
      {statusData?.quote && !statusData?.topic && !isGenerating && (
        <div style={cardStyle}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>Today&apos;s Quote</div>
          <p className="serif" style={{ fontSize: 20, fontStyle: 'italic', lineHeight: 1.6, color: 'var(--dash-text)' }}>&ldquo;{statusData.quote}&rdquo;</p>
          {statusData.author && <p style={{ marginTop: 8, fontSize: 14, color: 'var(--dash-muted)' }}>— {statusData.author}</p>}
        </div>
      )}

      {/* Video player */}
      {hasVideo && !isGenerating && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ background: '#0a0908', border: '1px solid #2a2720', borderRadius: 16, overflow: 'hidden' }}>
            <video
              key="aureus-preview"
              src={`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/video/stream?token=${typeof window !== 'undefined' ? localStorage.getItem('aureus_token') || '' : ''}&t=${Date.now()}`}
              controls
              playsInline
              style={{ width: '100%', maxHeight: 520, display: 'block', objectFit: 'contain', background: '#000' }}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/video/download?token=${typeof window !== 'undefined' ? localStorage.getItem('aureus_token') || '' : ''}`}
              target="_blank" rel="noopener noreferrer"
              className="btn btn-gold rounded-xl"
              style={{ height: 48, fontSize: 13, fontWeight: 700, textDecoration: 'none', gap: 6 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 20 }}>download</span>
              Download Video
            </a>
            {igConnected
              ? <div style={{ height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 13, color: '#4ade80', background: 'var(--dash-card)', border: '1px solid var(--dash-border)', borderRadius: 12 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 18 }}>check_circle</span>Auto-posting on
                </div>
              : <Link href="/connect/instagram" className="btn btn-outline rounded-xl"
                  style={{ height: 48, fontSize: 13, textDecoration: 'none', gap: 6 }}>
                  <IgIcon size={20} color="currentColor" />Connect IG
                </Link>
            }
          </div>
        </div>
      )}

      {/* IG status */}
      <div style={{ ...cardStyle, display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ width: 40, height: 40, borderRadius: 12, flexShrink: 0, background: igConnected ? 'rgba(34,197,94,.1)' : 'var(--dash-card-2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <IgIcon size={20} color={igConnected ? '#4ade80' : 'var(--dash-muted)'} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text)', marginBottom: 2 }}>Instagram Auto-Posting</div>
          <div style={{ fontSize: 12, color: 'var(--dash-muted)' }}>
            {igConnected ? 'Connected — videos post automatically at your scheduled time' : 'Optional — connect to enable auto-posting.'}
          </div>
        </div>
        {igConnected
          ? <span className="badge badge-success">Connected</span>
          : <Link href="/connect/instagram" className="btn btn-outline rounded-lg" style={{ padding: '6px 12px', fontSize: 12, textDecoration: 'none' }}>Connect</Link>
        }
      </div>
    </div>
  )
}

// ── HISTORY TAB ──────────────────────────────────────────────────────────────
function HistoryTab() {
  const { data: posts, isLoading } = useQuery({ queryKey: ['posts'], queryFn: () => postsApi.list(0, 30) })
  if (isLoading) return <PageLoader message="Loading post history…" />
  const cardStyle = { background: 'var(--dash-card)', border: '1px solid var(--dash-border)', borderRadius: 16 }

  if (!posts?.length) return (
    <div className="fade-up" style={{ textAlign: 'center', padding: '80px 20px' }}>
      <span className="material-symbols-outlined" style={{ fontSize: 48, color: 'var(--dash-muted)', display: 'block', marginBottom: 12 }}>video_library</span>
      <p style={{ color: 'var(--dash-muted)', fontSize: 15 }}>No videos generated yet.</p>
    </div>
  )

  const counts: Record<string, number> = {}
  for (const p of posts) counts[p.status] = (counts[p.status] || 0) + 1

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
        {[['success','Posted','badge-success'],['video_ready','Ready','badge-video_ready'],['failed','Failed','badge-failed'],['queued','In Queue','badge-queued']].map(([st,label,cls]) => (
          <div key={st} style={{ ...cardStyle, padding: '14px 10px', textAlign: 'center', borderRadius: 12 }}>
            <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--dash-text)', lineHeight: 1 }}>{counts[st] || 0}</div>
            <span className={`badge ${cls}`} style={{ marginTop: 6, display: 'inline-block', fontSize: 10 }}>{label}</span>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {posts.map((post: any) => (
          <div key={post.id} style={{ ...cardStyle, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, borderRadius: 12 }}>
            <div style={{ width: 48, height: 48, borderRadius: 10, flexShrink: 0, overflow: 'hidden', background: '#0a0908', border: '1px solid #2a2720', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--gold)', opacity: .7 }}>
                {post.status === 'success' || post.status === 'video_ready' ? 'play_circle' : 'movie'}
              </span>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              {post.quote_text && (
                <p style={{ fontSize: 13, fontWeight: 500, fontStyle: 'italic', color: 'var(--dash-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  &ldquo;{post.quote_text.substring(0,60)}…&rdquo;
                </p>
              )}
              <p style={{ fontSize: 11, color: 'var(--dash-muted)', marginTop: 3 }}>
                {format(new Date(post.scheduled_for), 'MMM d, yyyy · h:mm a')}
                {post.ig_auto_posted && <span style={{ color: '#4ade80', marginLeft: 8 }}>· Auto-posted ✓</span>}
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
              <span className={`badge badge-${post.status}`} style={{ fontSize: 10, whiteSpace: 'nowrap' }}>{STATUS_LABEL[post.status] || post.status}</span>
              {(post.status === 'video_ready' || post.status === 'success') && post.image_url && (
                <a href={`http://127.0.0.1:8000/api/video/post/${post.id}/download`}
                  className="btn btn-ghost rounded-lg" style={{ padding: '6px', textDecoration: 'none' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 18 }}>download</span>
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── SCHEDULE TAB ─────────────────────────────────────────────────────────────
function ScheduleTab({ user }: { user: any }) {
  const qc = useQueryClient()
  const { data: schedule, isLoading } = useQuery({ queryKey: ['schedule'], queryFn: () => scheduleApi.get().catch(() => null) })
  const [time, setTime] = useState('09:00')
  const [tz, setTz] = useState('UTC')
  const [saved, setSaved] = useState(false)
  const cardStyle = { background: 'var(--dash-card)', border: '1px solid var(--dash-border)', borderRadius: 16, padding: 24 }

  useEffect(() => {
    if (schedule) { setTime(schedule.hhmm_time); setTz(schedule.timezone) }
    else if (user?.timezone) setTz(user.timezone)
  }, [schedule, user])

  const saveMut = useMutation({
    mutationFn: () => scheduleApi.upsert({ hhmm_time: time, timezone: tz }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['schedule'] }); setSaved(true); setTimeout(() => setSaved(false), 3000) },
  })
  const toggleMut = useMutation({ mutationFn: () => schedule?.active ? scheduleApi.pause() : scheduleApi.resume(), onSuccess: () => qc.invalidateQueries({ queryKey: ['schedule'] }) })
  const skipMut   = useMutation({ mutationFn: () => scheduleApi.skipNext(), onSuccess: () => qc.invalidateQueries({ queryKey: ['schedule'] }) })

  if (isLoading) return <PageLoader message="Loading schedule…" />
  const TZ = ['UTC','America/New_York','America/Chicago','America/Los_Angeles','America/Toronto','Europe/London','Europe/Berlin','Asia/Kolkata','Asia/Dubai','Asia/Tokyo','Australia/Sydney']

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 480 }}>
      <div style={cardStyle}>
        <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 6, color: 'var(--dash-text)' }}>Daily Post Schedule</h3>
        <p style={{ fontSize: 13, color: 'var(--dash-muted)', marginBottom: 20, lineHeight: 1.6 }}>Aureus generates your video at this time every day.</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--dash-muted)', marginBottom: 8 }}>Time</label>
            <input type="time" value={time} onChange={e => setTime(e.target.value)} className="inp" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--dash-muted)', marginBottom: 8 }}>Timezone</label>
            <select value={tz} onChange={e => setTz(e.target.value)} className="inp">{TZ.map(t => <option key={t} value={t}>{t}</option>)}</select>
          </div>
          <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending} className="btn btn-gold rounded-xl" style={{ height: 48, fontSize: 14, fontWeight: 700, gap: 8 }}>
            {saveMut.isPending ? <><Spinner size={16} />Saving…</> : saved ? '✓ Schedule Saved' : 'Save Schedule'}
          </button>
        </div>
      </div>
      {schedule && (
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--dash-text)' }}>Status</h3>
            <span className={`badge ${schedule.active ? 'badge-success' : 'badge-skipped'}`}>{schedule.active ? 'Active' : 'Paused'}</span>
          </div>
          <div style={{ fontSize: 40, fontWeight: 900, color: 'var(--dash-text)', lineHeight: 1, marginBottom: 4 }}>{schedule.hhmm_time}</div>
          <div style={{ fontSize: 13, color: 'var(--dash-muted)', marginBottom: 20 }}>{schedule.timezone}</div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={() => toggleMut.mutate()} disabled={toggleMut.isPending} className="btn btn-outline rounded-xl" style={{ flex: 1, height: 44, fontSize: 13, gap: 6, color: schedule.active ? '#fbbf24' : '#4ade80' }}>
              {toggleMut.isPending ? <Spinner size={14} /> : schedule.active ? '⏸ Pause' : '▶ Resume'}
            </button>
            <button onClick={() => skipMut.mutate()} disabled={skipMut.isPending || schedule.skip_next} className="btn btn-outline rounded-xl" style={{ flex: 1, height: 44, fontSize: 13, gap: 6 }}>
              {skipMut.isPending ? <Spinner size={14} /> : schedule.skip_next ? '✓ Skip Set' : '⏭ Skip Next'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── SETTINGS TAB ─────────────────────────────────────────────────────────────
function SettingsTab({ user, refetchUser }: { user: any; refetchUser: () => void }) {
  const qc = useQueryClient()
  const [name, setName]         = useState(user?.name || '')
  const [handle, setHandle]     = useState(user?.ig_handle || '')
  const [theme, setTheme]       = useState(user?.video_theme || '')
  const [autoPost, setAutoPost] = useState(user?.auto_post_ig || false)
  const [saved, setSaved]       = useState(false)
  const cardStyle = { background: 'var(--dash-card)', border: '1px solid var(--dash-border)', borderRadius: 16, padding: 24 }

  useEffect(() => {
    if (user) { setName(user.name||''); setHandle(user.ig_handle||''); setTheme(user.video_theme||''); setAutoPost(user.auto_post_ig||false) }
  }, [user])

  const { data: igStatus, isLoading: igLoading } = useQuery({ queryKey: ['ig-status'], queryFn: () => instagramApi.status().catch(() => null) })
  const igConnected = igStatus?.status === 'connected'

  const saveMut = useMutation({
    mutationFn: () => userApi.update({ name, ig_handle: handle||null, video_theme: theme||null, auto_post_ig: autoPost }),
    onSuccess: () => { refetchUser(); setSaved(true); setTimeout(() => setSaved(false), 3000) },
  })
  const disconnectMut = useMutation({ mutationFn: () => instagramApi.disconnect(), onSuccess: () => qc.invalidateQueries({ queryKey: ['ig-status'] }) })

  const THEMES = ['','success and growth','resilience and perseverance','mindfulness and gratitude','leadership and vision','courage and taking risks']

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 480 }}>
      <div style={cardStyle}>
        <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: 'var(--dash-text)' }}>Profile</h3>
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--dash-muted)', marginBottom: 8 }}>Display Name</label>
          <input value={name} onChange={e => setName(e.target.value)} className="inp" placeholder="Your name" />
        </div>
        <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending} className="btn btn-gold rounded-xl" style={{ width: '100%', height: 48, fontSize: 14, fontWeight: 700, gap: 8 }}>
          {saveMut.isPending ? <><Spinner size={16} />Saving…</> : saved ? '✓ Saved' : 'Save Changes'}
        </button>
      </div>

      <div style={cardStyle}>
        <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: 'var(--dash-text)' }}>Video Settings</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--dash-muted)', marginBottom: 8 }}>Brand Handle</label>
            <input value={handle} onChange={e => setHandle(e.target.value)} className="inp" placeholder="@your_brand" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--dash-muted)', marginBottom: 8 }}>Quote Theme</label>
            <select value={theme} onChange={e => setTheme(e.target.value)} className="inp">
              {THEMES.map(t => <option key={t} value={t}>{t || 'Default (success & growth)'}</option>)}
            </select>
          </div>
          <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending} className="btn btn-gold rounded-xl" style={{ width: '100%', height: 48, fontSize: 14, fontWeight: 700, gap: 8 }}>
            {saveMut.isPending ? <><Spinner size={16} />Saving…</> : 'Save Video Settings'}
          </button>
        </div>
      </div>

      <div style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--dash-text)' }}>Instagram Auto-Posting</h3>
          <span style={{ fontSize: 11, padding: '3px 8px', borderRadius: 9999, background: 'var(--dash-card-2)', color: 'var(--dash-muted)' }}>Optional</span>
        </div>
        <p style={{ fontSize: 13, color: 'var(--dash-muted)', marginBottom: 16, lineHeight: 1.6 }}>Videos are always available for download. Connect Instagram only for auto-posting.</p>
        {igLoading ? <div style={{ textAlign: 'center', padding: '20px 0' }}><Spinner /></div>
          : igConnected ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', borderRadius: 12, background: 'rgba(34,197,94,.07)', border: '1px solid rgba(34,197,94,.2)' }}>
                <span className="material-symbols-outlined" style={{ color: '#4ade80', fontSize: 22 }}>check_circle</span>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text)' }}>@{igStatus?.connection?.ig_username}</div>
                  <div style={{ fontSize: 12, color: 'var(--dash-muted)' }}>Connected and ready</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderRadius: 12, background: 'var(--dash-card-2)' }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text)' }}>Auto-post videos</div>
                  <div style={{ fontSize: 12, color: 'var(--dash-muted)', marginTop: 2 }}>Post to Instagram at scheduled time</div>
                </div>
                <button onClick={() => { const n = !autoPost; setAutoPost(n); userApi.update({ auto_post_ig: n }) }}
                  className={`toggle-track ${autoPost ? 'on' : ''}`} style={{ width: 42, height: 24, cursor: 'pointer', border: 'none', flexShrink: 0 }}>
                  <div className="toggle-thumb" />
                </button>
              </div>
              <button onClick={() => disconnectMut.mutate()} disabled={disconnectMut.isPending} className="btn btn-danger rounded-xl" style={{ width: '100%', height: 44, fontSize: 13, gap: 8 }}>
                {disconnectMut.isPending ? <><Spinner size={14} />Disconnecting…</> : 'Disconnect Instagram'}
              </button>
            </div>
          ) : (
            <Link href="/connect/instagram" className="btn btn-outline rounded-xl" style={{ width: '100%', height: 48, fontSize: 14, fontWeight: 700, textDecoration: 'none', gap: 8 }}>
              <IgIcon size={20} color="currentColor" />Connect Instagram Account
            </Link>
          )
        }
      </div>
    </div>
  )
}

// ── MAIN DASHBOARD ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('today')
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) { router.replace('/auth/login') }
    else { setAuthChecked(true) }
  }, [])

  const { data: user, isLoading: userLoading, refetch: refetchUser } = useQuery({
    queryKey: ['user'], queryFn: () => userApi.me(), enabled: authChecked,
  })

  const TAB_TITLE: Record<Tab, string> = { today: "Today's Video", history: 'Post History', schedule: 'Schedule', settings: 'Settings' }

  if (!authChecked || userLoading) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--dash-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16 }}>
        <div style={{ width: 56, height: 56, borderRadius: '50%', border: '3px solid var(--dash-border)', borderTopColor: 'var(--gold)', animation: 'dashSpin 0.8s linear infinite' }} />
        <p style={{ color: 'var(--dash-muted)', fontSize: 14 }}>Loading…</p>
      </div>
    )
  }

  return (
    <div className="dash-root">
      <Sidebar tab={tab} setTab={setTab} user={user} />
      <div className="sidebar-main" style={{ flex: 1 }}>
        <header style={{ position: 'sticky', top: 0, zIndex: 30, background: 'var(--dash-nav)', borderBottom: '1px solid var(--dash-border)', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', backdropFilter: 'blur(8px)', transition: 'background .28s, border-color .28s' }}>
          <h1 style={{ fontSize: 15, fontWeight: 700, color: 'var(--dash-text)' }}>{TAB_TITLE[tab]}</h1>
          {tab === 'today' && (
            <Link href="/connect/instagram" style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', textDecoration: 'none' }}>+ Connect Instagram</Link>
          )}
        </header>
        <main style={{ maxWidth: 640, margin: '0 auto', padding: '24px 16px 60px' }}>
          {tab === 'today'    && <TodayTab user={user} />}
          {tab === 'history'  && <HistoryTab />}
          {tab === 'schedule' && <ScheduleTab user={user} />}
          {tab === 'settings' && <SettingsTab user={user} refetchUser={refetchUser} />}
        </main>
      </div>
    </div>
  )
}
