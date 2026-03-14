# Free AI Video Generation — Complete Guide
> All options tested, ranked by quality. No credit card required for top picks.

---

## Quick Start (Pick One)

### 🥇 Best Free: D-ID  — Realistic talking head, 2-week trial
```
1. Sign up: https://studio.d-id.com  (no credit card)
2. Dashboard → top-right avatar → API
3. Copy the "Basic xxxxxxxx" token
4. Add to backend/.env:  DID_API_KEY=Basic xxxxxxxx
5. Restart backend → generate video
```
**What you get:** A photorealistic person on screen reading your script.  
**Free:** ~5 minutes of video, watermark visible on trial.

---

### 🥈 HeyGen — 1 free video per account
```
1. Sign up: https://heygen.com  (no credit card)
2. Settings → API → Generate API Token
3. Add to backend/.env:  HEYGEN_API_KEY=your-token
```
**What you get:** Professional avatar presenter, best lip-sync quality.  
**Free:** 1 credit = 1 minute.

---

### 🥉 Replicate — Free limited runs via GitHub login
```
1. Sign up: https://replicate.com  (use GitHub — instant)
2. Account → API Tokens → copy token
3. Add to backend/.env:  REPLICATE_API_TOKEN=r8_xxxxx
```
**What you get:** AI scene footage (Zeroscope, AnimateDiff models).  
**Free:** Limited runs, no CC needed. After limit: add $5 credit.

---

### 🆓 Hugging Face — Completely free, no sign-up needed
```
1. Nothing to set up — works automatically as fallback
2. Optional: sign up at huggingface.co for higher limits
3. Add to backend/.env:  HF_TOKEN=hf_xxxxx  (optional)
```
**What you get:** ModelScope text-to-video (lower quality, truly free forever).

---

## Full Comparison Table

| Provider | Type | Quality | Free Tier | CC Needed? | Setup Time |
|----------|------|---------|-----------|------------|------------|
| **D-ID** | Talking head | ★★★★★ | 2 weeks, ~5 min | ❌ No | 5 min |
| **HeyGen** | Talking head | ★★★★★ | 1 video (1 min) | ❌ No | 5 min |
| **Replicate** | Scene clips | ★★★★☆ | Limited runs | ❌ No | 2 min |
| **Hugging Face** | Scene clips | ★★★☆☆ | Unlimited | ❌ No | 0 min |
| fal.ai | Scene clips | ★★★★☆ | $10 credit | ✅ Yes | 5 min |
| RunwayML | Cinematic | ★★★★☆ | $15/mo | ✅ Yes | 10 min |
| Luma AI | Hyper-real | ★★★★★ | $29.99/mo | ✅ Yes | 10 min |

---

## What Each Video Looks Like

### D-ID / HeyGen (Talking Head)
```
┌─────────────────────────┐
│                         │
│    [person's face]      │  ← Photorealistic avatar
│    [talking, gesturing] │     reading your script
│                         │
│  "AI is reshaping every │  ← Natural lip-sync
│   industry right now..."│
│                         │
└─────────────────────────┘
```
Best for: News anchor style, business content, educational videos

### Replicate / HuggingFace (Scene Clips)
```
┌─────────────────────────┐
│  [city skyline footage] │  ← AI-generated scene
│  [golden hour light]    │     matching your prompt
│  [data streams visuals] │
│                         │
│  + narration audio      │  ← OpenAI TTS voice overlay
└─────────────────────────┘
```
Best for: Atmospheric/cinematic content, abstract topics

---

## How the Pipeline Works

```
Click "Generate Today's Video"
          │
          ▼
  GPT-4o-mini picks topic
  + writes 20s script
  + 4 scene descriptions
          │
          ▼
  OpenAI TTS → MP3 narration
  (voice: "onyx" — professional male)
          │
          ▼
  Try AI video (in order):
  D-ID → HeyGen → Replicate → HuggingFace
          │
          ▼
  Mix audio + video → MP4
  (PIL fallback if all fail)
          │
          ▼
  Ready to download + post
```

---

## Tips for Demo

1. **No API keys at all?**  
   The PIL renderer (gold animated text + particles + TTS voice) still looks great for a demo.

2. **Just want talking head for free?**  
   Sign up at D-ID (2 min), paste the API key → you get a real person on screen.

3. **Want the best quality for free?**  
   Use D-ID for the trial + HuggingFace as permanent fallback. Both free, no CC.

4. **Only have OpenAI key?**  
   GPT-4o-mini script + "onyx" voice + PIL video = surprisingly professional.

---

## Upgrade Path (After Demo)

| Budget | Best Option | Why |
|--------|-------------|-----|
| $0 | D-ID trial + HF | Real person + free forever |
| $5 | Replicate credits | ~200 video clips |
| $10 | fal.ai credits | Kling 1.6, best value |
| $29/mo | Luma unlimited | No per-video anxiety |
| $29/mo | HeyGen starter | Unlimited avatar videos |
