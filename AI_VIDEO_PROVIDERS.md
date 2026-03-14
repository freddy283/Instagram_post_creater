# AI Video Providers — Research & Comparison
> For realistic video with people, locations, and cinematic footage

---

## The Goal
Generate a **20-second news-highlight video** that looks like:
- A real person (news anchor) presenting the topic, OR
- Cinematic footage of real-world locations and scenes
- High-quality narration audio
- Professional broadcast quality

---

## Provider Comparison

| Provider | Style | Quality | Cost | Setup Time | Best For |
|----------|-------|---------|------|------------|----------|
| **HeyGen** | Avatar presenter | ★★★★★ | $29/mo | 5 min | News anchor on screen |
| **Synthesia** | Avatar presenter | ★★★★★ | $29/mo | 5 min | Corporate presenter style |
| **RunwayML Gen-3** | Cinematic footage | ★★★★☆ | $0.05/s | 10 min | Scene-based cinematic |
| **Luma Dream Machine** | Hyper-realistic | ★★★★★ | $0.14/s | 10 min | Most photorealistic |
| **fal.ai (Kling 1.6)** | Realistic + people | ★★★★☆ | $0.028/s | 5 min | Best value, great quality |
| **Pika 2.0** | Stylized video | ★★★★ | $8/mo | 5 min | Creative/stylized |
| **D-ID** | Talking head | ★★★★ | $5.9/mo | 5 min | Simple presenter |

---

## Recommended for Client Demo

### 🥇 Option 1 — HeyGen (Most Impressive)
**What you get:** A photorealistic avatar person on screen, reading your news script aloud, with realistic lip-sync and natural gestures.

**Setup (5 minutes):**
1. Go to https://heygen.com → Sign Up (free trial = 1 free video/month)
2. Dashboard → Settings → API → copy your API key
3. Add to `.env`: `HEYGEN_API_KEY=your-key`
4. Restart backend → generate video

**What the output looks like:** A professional news presenter reading: *"Artificial intelligence is reshaping every industry. From healthcare to finance..."* — with a real-looking face, natural voice, and broadcast-quality visuals.

---

### 🥈 Option 2 — fal.ai / Kling (Best Value)
**What you get:** AI-generated realistic footage matching your scene descriptions — people in offices, city skylines, hands typing, etc. Combined with TTS narration.

**Setup (5 minutes):**
1. Go to https://fal.ai → Sign Up → Add $5 credit
2. Dashboard → API Keys → copy key
3. Add to `.env`: `FAL_KEY=your-key`
4. Install: `pip install fal-client`
5. Restart backend

**Cost:** 4 clips × 5s × $0.028/s ≈ **$0.56 per video**

---

### 🥉 Option 3 — RunwayML (Most Established)
**What you get:** Cinematic footage of scenes, environments, and actions. Very high quality and consistent.

**Setup:**
1. Go to https://app.runwayml.com → Sign Up → API section
2. Copy API key → add to `.env`: `RUNWAY_API_KEY=your-key`
3. Install: `pip install runwayml`

**Cost:** 4 clips × 5s × $0.05/s ≈ **$1.00 per video**

---

## Current Pipeline (No API Key)

Without any AI video key, the system uses the PIL-based renderer which produces:
- Animated gold text on dark background
- Word-by-word quote reveal
- Particle effects and glow
- OpenAI TTS voice narration (if OPENAI_API_KEY is set)
- Falls back to sine-tone audio otherwise

This is functional for demo but not "realistic video with people."

---

## Quick Start for Demo Today

**Fastest path to impressive demo:**
1. Sign up at https://heygen.com (free account)
2. Get API key from Settings → API
3. Add `HEYGEN_API_KEY=your-key` to `backend/.env`
4. Restart backend: `uvicorn app.main:app --port 8000 --reload`
5. Generate a video — you'll get a real person presenting the news

**If you only have OpenAI key:**
- Set `OPENAI_API_KEY` in `.env`
- You'll get: GPT-4o-mini news script + "onyx" voice narration + cinematic text animation
- Quality is surprisingly good for a text-based video

---

## How the Pipeline Works

```
Click "Generate" →
  1. GPT-4o-mini picks trending topic + writes 20s script + 4 scene descriptions
  2. OpenAI TTS converts script to MP3 (voice: onyx)
  3. Try AI video providers in order:
       a. HeyGen → photorealistic avatar presenter
       b. RunwayML → cinematic scene clips
       c. Luma → hyper-realistic footage
       d. fal.ai → Kling 1.6 clips
  4. If none available → PIL fallback (animated text + gold particles)
  5. Combine video + narration audio → MP4
  6. Available for preview + download
```
