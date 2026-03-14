'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { isAuthenticated } from '@/lib/api'
import { useTheme } from '@/lib/theme'

const DEMOS = [
  { quote: 'Stop waiting for the perfect moment. Take the moment and make it perfect.', author: '— Marcus Aurelius' },
  { quote: 'Discipline is the bridge between your goals and your results.', author: '— Jim Rohn' },
  { quote: 'Every morning you have two choices: continue to sleep with your dreams, or wake up and chase them.', author: '— Carmelo Anthony' },
]

function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const dark = theme === 'dark'
  return (
    <button onClick={toggle} className="theme-toggle" aria-label="Toggle theme">
      <span style={{ fontSize: 14 }}>{dark ? '☀️' : '🌙'}</span>
      <div className={`toggle-track ${dark ? '' : 'on'}`}><div className="toggle-thumb" /></div>
      <span>{dark ? 'Light' : 'Dark'}</span>
    </button>
  )
}

export default function Landing() {
  const [qi, setQi] = useState(0)
  const [vis, setVis] = useState(true)
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    setAuthed(isAuthenticated())
    const t = setInterval(() => {
      setVis(false)
      setTimeout(() => { setQi(i => (i + 1) % DEMOS.length); setVis(true) }, 400)
    }, 5000)
    return () => clearInterval(t)
  }, [])

  const demo = DEMOS[qi]

  return (
    <div style={{ background: 'var(--bg)', color: 'var(--text)', minHeight: '100vh' }}>

      {/* ── Nav ────────────────────────────────────────────────────────── */}
      <header style={{ background: 'var(--nav-bg)', borderBottom: '1px solid var(--border-light)' }}
        className="fixed top-0 w-full z-50 backdrop-blur-md">
        <div className="flex items-center justify-between px-6 md:px-16 lg:px-32 py-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined" style={{ color: 'var(--gold)', fontSize: 24 }}>movie_filter</span>
            <span className="font-bold tracking-[.12em] uppercase text-lg" style={{ color: 'var(--text)' }}>Aureus</span>
          </div>
          <nav className="hidden md:flex items-center gap-8">
            {['#how', '#features', '#demo'].map((h, i) => (
              <a key={h} href={h} style={{ color: 'var(--text-2)', fontSize: 14 }}
                className="transition-colors hover:text-white">{['How It Works', 'Features', 'Demo'][i]}</a>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            {authed
              ? <Link href="/dashboard" className="btn btn-gold text-xs tracking-widest uppercase px-5 py-2.5 rounded-full">Dashboard</Link>
              : <Link href="/auth/register" className="btn btn-primary text-xs tracking-widest uppercase px-5 py-2.5 rounded-full">Start Free</Link>
            }
          </div>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="min-h-screen flex items-center pt-20 px-6 md:px-16 lg:px-32">
        <div className="max-w-7xl mx-auto w-full grid md:grid-cols-2 gap-12 items-center">
          {/* Left copy */}
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full"
              style={{ background: 'rgba(212,175,55,.12)', border: '1px solid rgba(212,175,55,.25)' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--gold)' }}>auto_awesome</span>
              <span style={{ color: 'var(--gold)', fontSize: 12, fontWeight: 700, letterSpacing: '.1em' }}>AI VIDEO AUTOMATION</span>
            </div>
            <h1 className="serif text-5xl md:text-6xl lg:text-7xl leading-[1.05]" style={{ color: 'var(--text)' }}>
              A fresh<br />
              <span style={{ color: 'var(--gold)' }} className="italic">motivational</span><br />
              video every day.
            </h1>
            <p style={{ color: 'var(--text-2)', fontSize: 18, lineHeight: 1.7, maxWidth: 480 }}>
              Aureus generates stunning 45-second cinematic videos with AI-written quotes and ambient audio — automatically, every morning. Download and post, or connect Instagram to auto-publish.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/auth/register" className="btn btn-gold text-sm tracking-wide px-8 py-4 rounded-full">
                Generate My First Video
              </Link>
              <a href="#demo" className="btn btn-outline text-sm tracking-wide px-8 py-4 rounded-full">
                See Demo →
              </a>
            </div>
            <div className="flex items-center gap-6 pt-2">
              {[['movie_filter','AI-Generated'],['download','Download & Post'],['schedule','Daily Schedule']].map(([icon, label]) => (
                <div key={label} className="flex items-center gap-2" style={{ color: 'var(--text-2)', fontSize: 13 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--gold)' }}>{icon}</span>
                  {label}
                </div>
              ))}
            </div>
          </div>

          {/* Right — video preview card */}
          <div className="flex justify-center">
            <div className="video-card" style={{ width: 280, maxWidth: '100%', aspectRatio: '9/16' }}>
              {/* Mock phone frame */}
              <div className="relative h-full flex flex-col items-center justify-center p-8 text-center"
                style={{ background: 'linear-gradient(160deg,#0a0908 0%,#1a1510 50%,#0a0908 100%)' }}>
                {/* Top brand */}
                <div className="absolute top-8 w-full text-center">
                  <div className="text-xs font-bold tracking-[.3em] uppercase" style={{ color: 'var(--gold)' }}>Aureus</div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--text-2)' }}>Daily Wisdom</div>
                </div>
                {/* Decorative lines */}
                <div className="absolute" style={{ top: 80, left: 24, right: 24, height: 1, background: 'linear-gradient(90deg,transparent,#d4af3755,transparent)' }} />
                <div className="absolute" style={{ bottom: 130, left: 24, right: 24, height: 1, background: 'linear-gradient(90deg,transparent,#d4af3755,transparent)' }} />
                {/* Quote */}
                <div style={{ opacity: vis ? 1 : 0, transition: 'opacity .4s ease' }}>
                  <p className="serif italic text-base leading-relaxed" style={{ color: '#d4af37' }}>
                    &ldquo;{demo.quote}&rdquo;
                  </p>
                  <p className="mt-4 text-xs tracking-widest uppercase" style={{ color: '#6b6050' }}>{demo.author}</p>
                </div>
                {/* Bottom CTA */}
                <div className="absolute bottom-8 text-center">
                  <div className="text-xs" style={{ color: '#6b6050' }}>Follow for daily wisdom</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────── */}
      <section id="how" style={{ background: 'var(--bg-surface)' }} className="py-28 px-6 md:px-16 lg:px-32">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="serif text-4xl md:text-5xl mb-4">How It Works</h2>
            <div className="w-16 h-px mx-auto" style={{ background: 'var(--gold)' }} />
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: '01', icon: 'edit_note',       title: 'AI Writes the Script',    desc: 'Every morning, GPT-4 writes a fresh motivational quote in your chosen theme. Unique, never repeated.' },
              { step: '02', icon: 'movie_creation',  title: 'Video Renders Automatically', desc: 'A cinematic 45-second Reel is generated — gold typography, ambient audio, word-by-word reveal animation.' },
              { step: '03', icon: 'download',         title: 'Download or Auto-Post',   desc: 'Download and post manually, or connect Instagram once and let Aureus publish automatically every day.' },
            ].map(c => (
              <div key={c.step} className="glass p-8 rounded-2xl space-y-4">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-black tracking-widest" style={{ color: 'var(--gold)', opacity: .5 }}>{c.step}</span>
                  <span className="material-symbols-outlined text-3xl" style={{ color: 'var(--gold)' }}>{c.icon}</span>
                </div>
                <h3 className="text-lg font-bold">{c.title}</h3>
                <p style={{ color: 'var(--text-2)', fontSize: 14, lineHeight: 1.7 }}>{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────── */}
      <section id="features" className="py-28 px-6 md:px-16 lg:px-32">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="serif text-4xl md:text-5xl mb-4">Everything You Need</h2>
            <div className="w-16 h-px mx-auto" style={{ background: 'var(--gold)' }} />
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { icon: 'auto_awesome',   title: 'Fresh AI Content Daily',       desc: 'GPT-4o-mini generates unique quotes every day — no repeats, no manual work.' },
              { icon: 'music_note',     title: 'Built-in Ambient Audio',       desc: 'Deep harmonic tones add cinematic depth. No royalty issues — generated on the fly.' },
              { icon: 'schedule',       title: 'Flexible Scheduling',          desc: 'Set your posting time and timezone. Aureus handles the rest, every single day.' },
              { icon: 'download',       title: 'Download-First Approach',      desc: 'Always get your video first. Instagram auto-posting is optional — no lock-in.' },
              { icon: 'palette',        title: 'Your Brand on Every Frame',    desc: 'Add your Instagram handle as watermark. Every video is instantly recognisable.' },
              { icon: 'instagram',      title: 'Optional Instagram Auto-Post', desc: 'Connect once and forget. Aureus posts as a Reel at your chosen time automatically.' },
            ].map(f => (
              <div key={f.title} className="glass p-6 rounded-xl flex gap-4">
                <span className="material-symbols-outlined text-2xl flex-shrink-0 mt-0.5" style={{ color: 'var(--gold)' }}>{f.icon}</span>
                <div>
                  <h3 className="font-bold mb-1">{f.title}</h3>
                  <p style={{ color: 'var(--text-2)', fontSize: 14, lineHeight: 1.65 }}>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Demo quote ───────────────────────────────────────────────── */}
      <section id="demo" style={{ background: 'var(--bg-surface)' }} className="py-28 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <span className="text-xs font-black tracking-[.4em] uppercase" style={{ color: 'var(--gold)' }}>Live Demo</span>
          <div className="mt-8" style={{ opacity: vis ? 1 : 0, transition: 'opacity .4s ease' }}>
            <p className="serif italic text-3xl md:text-4xl leading-tight" style={{ color: 'var(--text)' }}>
              &ldquo;{demo.quote}&rdquo;
            </p>
            <p className="mt-6 text-sm tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>{demo.author}</p>
          </div>
          <p className="mt-8 text-sm" style={{ color: 'var(--text-2)' }}>Quotes rotate every 5 seconds — AI generates a fresh one for your video every day.</p>
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────── */}
      <section className="py-28 px-6 text-center">
        <div className="max-w-xl mx-auto glass p-12 rounded-3xl">
          <h2 className="serif text-3xl md:text-4xl mb-4">Start generating today.</h2>
          <p className="mb-10" style={{ color: 'var(--text-2)', fontSize: 15, lineHeight: 1.7 }}>
            Free to start. No credit card. Your first video generates in under 90 seconds.
          </p>
          <Link href="/auth/register" className="btn btn-gold text-sm tracking-wide uppercase px-10 py-4 rounded-full w-full" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            Create Free Account
          </Link>
          <p className="mt-6 text-xs" style={{ color: 'var(--text-muted)' }}>
            Already have an account? <Link href="/auth/login" style={{ color: 'var(--gold)' }}>Log in</Link>
          </p>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer style={{ borderTop: '1px solid var(--border-light)' }} className="py-10 px-6 text-center">
        <div className="font-bold tracking-[.2em] uppercase mb-3">Aureus</div>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>© {new Date().getFullYear()} Aureus. AI-powered video automation.</p>
      </footer>
    </div>
  )
}
