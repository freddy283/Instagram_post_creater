# Aureus MVP — Complete Setup Guide
> Works on Windows 10/11 and Linux (Ubuntu/Debian)

---

## What was fixed in this version
1. **Auth bug** — Dashboard now properly redirects to login if unauthenticated OR if token is expired/invalid (401 auto-logout)
2. **Video generation** — Now generates a spoken narration script via OpenAI GPT-4o-mini, converts it to voice with OpenAI TTS (voice: "onyx"), and renders a cinematic 20-30s video with animated particles and glow typography

---

## Prerequisites

### Windows
| Tool | Install |
|------|---------|
| Python 3.11+ | https://www.python.org/downloads/ (✅ "Add to PATH") |
| Node.js 18+ | https://nodejs.org/ |
| ffmpeg | See below |

**Install ffmpeg on Windows:**
```powershell
# Option A — winget (easiest)
winget install Gyan.FFmpeg

# Option B — manual
# 1. Download https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
# 2. Extract → rename folder to "ffmpeg" → move to C:\ffmpeg\
# 3. Add C:\ffmpeg\bin to System PATH (search "Edit environment variables")
# 4. Restart terminal → verify: ffmpeg -version
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip nodejs npm ffmpeg -y
# Verify
ffmpeg -version && node -v && python3 --version
```

---

## Step 1 — Configure environment

Edit `backend/.env`:
```env
APP_ENV=development
SECRET_KEY=any-long-random-string-here-change-this
DATABASE_URL=sqlite:///./dailyquote.db

# Required for AI script + TTS (both use the same key)
OPENAI_API_KEY=sk-your-real-key-here
OPENAI_MODEL=gpt-4o-mini

VIDEO_THEME=success, growth and daily motivation
BRAND_HANDLE=@your_brand
VIDEOS_DIR=./videos

ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

> 💡 **Without OPENAI_API_KEY**: videos still generate with fallback quotes and sine-tone audio. Set the key for full AI script + TTS voice.

---

## Step 2 — Backend setup

### Windows (PowerShell / Command Prompt)
```powershell
cd aureus_mvp\backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (First run only) create the database
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(engine)"

# Start the backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Linux / Mac
```bash
cd aureus_mvp/backend

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# (First run only) create the database
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(engine)"

# Start the backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

✅ You should see: `Uvicorn running on http://127.0.0.1:8000`  
Test it: open http://127.0.0.1:8000/docs in your browser

---

## Step 3 — Frontend setup

Open a **new terminal** (keep backend running):

### Windows
```powershell
cd aureus_mvp\frontend
npm install
npm run dev
```

### Linux / Mac
```bash
cd aureus_mvp/frontend
npm install
npm run dev
```

✅ You should see: `ready on http://localhost:3000`

---

## Step 4 — Test the app

1. Open http://localhost:3000
2. Click **"Create Free Account"** → register with any email/password
3. Go to **Dashboard → Today's Video** → click **"Generate Today's Video"**
4. Wait ~30-60 seconds (progress bar shows)
5. Video plays in browser — download with the gold button

### Test the auth fix
1. Log out (bottom of sidebar)
2. Type http://localhost:3000/dashboard directly in the browser
3. ✅ You should be immediately redirected to `/auth/login`
4. If you had a browser tab open with an old session and the token expires, the next API call auto-redirects too

---

## Video generation — What happens

```
User clicks "Generate" →
  1. GPT-4o-mini writes a 20-25s spoken script about today's theme
  2. OpenAI TTS (voice: "onyx") converts script to MP3 audio
  3. PIL renders 750 frames at 1080×1920 with:
       - Warm gradient background with animated gold particles
       - Word-by-word quote reveal with glow effect
       - Decorative gold rules and diamond ornaments
       - Vignette and fade-to-black
  4. ffmpeg encodes frames + TTS audio → MP4
  5. Video available for download + browser preview
```

**Without OPENAI_API_KEY**: Steps 1 and 2 are skipped; fallback quote and ambient sine-tone audio are used instead.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ffmpeg not found` | See ffmpeg install section above |
| `ModuleNotFoundError` | Make sure venv is activated (`source venv/bin/activate` or `venv\Scripts\activate`) |
| Frontend can't connect to backend | Make sure backend is running on port 8000 |
| Videos folder permission error | `mkdir -p backend/videos && chmod 755 backend/videos` |
| OpenAI quota error | Check https://platform.openai.com/usage — video falls back to sine audio automatically |
| Dashboard still accessible without login | Clear browser localStorage: DevTools → Application → Local Storage → delete `aureus_token` |

---

## Best AI services for video + audio (research)

For production-grade video generation, these are the leading options:

### Script generation
- **OpenAI GPT-4o-mini** ✅ (already integrated) — fast, cheap, excellent quality

### Text-to-speech (narration)
- **OpenAI TTS** ✅ (already integrated) — voice "onyx" is ideal for motivational content; $15/1M chars
- **ElevenLabs** — highest quality, most natural voices; free tier 10k chars/month; ~$22/month for production
- **Google Cloud TTS** — reliable, many voices, competitive pricing

### AI video generation (next level)
- **RunwayML Gen-3 Alpha** — text-to-video, cinematic quality; $35/month starter
- **Pika Labs** — text/image-to-video; good for dynamic backgrounds
- **Stable Video Diffusion** — open source, self-hostable

### Background music
- **Suno AI** — generates royalty-free background music from text prompts
- **ElevenLabs Sound Effects** — ambient sounds, royalty-free

> For the current demo: OpenAI GPT-4o-mini (script) + OpenAI TTS (voice) + PIL + ffmpeg (rendering) is the optimal stack — all in one API key, excellent quality, no extra services needed.
