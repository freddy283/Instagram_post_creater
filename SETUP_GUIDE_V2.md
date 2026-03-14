# Aureus v2 — Setup Guide
> Beautiful animated social videos, 100% free stack

---

## What's new in v2

| Feature | v1 (old) | v2 (new) |
|---------|----------|----------|
| Video | Static single image | **4-scene animated video** |
| Animation | None | **Ken Burns effect per scene** |
| Transitions | None | **Smooth cross-dissolve** |
| Text | Always visible | **Fade in per scene** |
| TTS | OpenAI only (paid) | **edge-tts FREE + pyttsx3 offline** |
| Script | OpenAI only (paid) | **Groq LLaMA free + fallbacks** |
| Backgrounds | Black gradient | **Real photos (Pixabay) + gradient** |

Works with **zero API keys** — everything has a beautiful fallback.

---

## Quick Start (5 minutes)

### Step 1 — Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

> This installs `edge-tts`, `groq`, and `pyttsx3` automatically.

### Step 2 — Copy env file
```bash
cp .env.example .env
```

### Step 3 — Run (no API keys needed!)
```bash
uvicorn app.main:app --reload
```

The app works out-of-the-box with gradient backgrounds + ambient audio.
Videos will be far better than v1 already.

---

## Free API Keys (10 minutes each, no credit card)

### 🥇 Groq — FREE script generation (highly recommended)
Gives you LLaMA-3.3-70b quality scripts for free.

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up with GitHub/Google (instant)
3. API Keys → Create API Key
4. Add to `.env`:
   ```
   GROQ_API_KEY=gsk_...
   ```

Free tier: **6,000 tokens/min** — enough for hundreds of videos/day.

---

### 🥈 Pixabay — FREE background photos (highly recommended)
Gives real cinematic photographs as video backgrounds.

1. Go to [pixabay.com/api/docs](https://pixabay.com/api/docs/)
2. Sign up (free, instant)
3. Your API key appears on the API docs page
4. Add to `.env`:
   ```
   PIXABAY_API_KEY=...
   ```

Free tier: **100 requests/minute** — more than enough.

---

### 🥉 edge-tts — FREE TTS (already installed!)
No key needed. `pip install edge-tts` is all you need.

Uses Microsoft's Neural voices (same as Azure TTS) for free.
Voice used: **en-US-GuyNeural** (professional male, American accent).

Change voice in `video_generator.py` → `_tts_edge()`:
- `en-GB-RyanNeural` — British male
- `en-US-JennyNeural` — Professional female
- `en-IN-NeerjaNeural` — Indian female
- `en-AU-WilliamNeural` — Australian male

---

## How the Video Pipeline Works

```
Click "Generate Video"
       │
       ▼
① SCRIPT GENERATION
  Groq LLaMA-3.3 → 4 sentences + 4 scene descriptions + quote
  (fallback: 9 built-in cinematic topics)
       │
       ▼
② TTS NARRATION
  edge-tts → en-US-GuyNeural → MP3
  (fallback: pyttsx3 offline → ambient sine tone)
       │
       ▼
③ BACKGROUND IMAGES (×4)
  Pixabay API → real photograph matching scene description
  (fallback: PIL gradient with gold arc decoration)
       │
       ▼
④ SCENE VIDEOS (×4, each 5 seconds)
  Ken Burns (zoom/pan) + text overlay + fade in/out
  via ffmpeg zoompan + overlay filter
       │
       ▼
⑤ SCENE TRANSITIONS
  xfade cross-dissolve at 0.5s between each scene
       │
       ▼
⑥ AUDIO MIX
  Narration MP3 mixed with combined video
  Total duration: ~20 seconds
       │
       ▼
⑦ READY
  Download / Auto-post to Instagram
```

---

## Video Structure

```
Scene 1 (0-5s)   Scene 2 (4.5-9.5s)  Scene 3 (9-14s)   Scene 4 (13.5-18.5s)
┌─────────────┐  ┌──────────────────┐  ┌─────────────┐  ┌──────────────────┐
│ [Photo 1]   │  │ [Photo 2]        │  │ [Photo 3]   │  │ [Photo 4]        │
│ Ken Burns ↗ │  │ Ken Burns →      │  │ Ken Burns ↙ │  │ Ken Burns ←      │
│             │  │                  │  │             │  │                  │
│ "Sentence 1"│  │ "Sentence 2"     │  │ "Sentence 3"│  │ ❝ Famous Quote ❞ │
│             │  │                  │  │             │  │ — Author Name    │
│ ●○○○        │  │ ○●○○             │  │ ○○●○        │  │ ○○○●             │
│ AUREUS      │  │ AUREUS           │  │ AUREUS      │  │ AUREUS           │
└─────────────┘  └──────────────────┘  └─────────────┘  └──────────────────┘
     ↘ 0.5s xfade ↙           ↘ 0.5s xfade ↙           ↘ 0.5s xfade ↙
                    ────────────── 18-20 seconds total ──────────────
```

---

## Customisation

### Change number of scenes
In `video_generator.py`, change `SCENE_DUR = 5` (seconds) and the `_split_into_scenes()` call.

### Change voice
Edit `_tts_edge()`: change `"en-US-GuyNeural"` to any voice from [edge-tts voices list](https://github.com/rany2/edge-tts#list-of-voices).

### Change Ken Burns style
Edit `SCENE_KB` list — each entry has `z_expr` (zoom), `x_expr` (pan X), `y_expr` (pan Y).

### Change gradient colours
Edit `SCENE_COLORS` — each tuple is `(top_RGB, bottom_RGB)`.

### Change font size
Edit `_render_overlay()` — change `_font(58, bold=True)` to any size.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ffmpeg not found` | `sudo apt-get install ffmpeg` |
| `edge-tts not found` | `pip install edge-tts` |
| `groq not found` | `pip install groq` |
| No Pixabay images | Sign up free at pixabay.com/api/docs |
| Video too slow | Reduce `FPS = 30` to `FPS = 24` in video_generator.py |
| Text too big | Reduce starting font size in `_render_overlay()` |

---

## Instagram Auto-posting

1. Create a Facebook Developer App at [developers.facebook.com](https://developers.facebook.com)
2. Add Instagram Basic Display + Instagram Content Publishing permissions
3. Add to `.env`:
   ```
   INSTAGRAM_APP_ID=...
   INSTAGRAM_APP_SECRET=...
   PUBLIC_URL=https://your-domain.com   # must be public HTTPS
   ```
4. Use ngrok for local testing: `ngrok http 8000`
