"""
Aureus AI Video Generation v3.1
=================================
Free-first priority chain:

  1. D-ID        — Talking avatar      FREE 2-week trial  (studio.d-id.com)
  2. HeyGen      — Talking avatar      FREE 1 credit      (heygen.com)
  3. Kling       — Cinematic clips     FREE 66 credits/day (klingai.com/dev)
  4. Replicate   — Wan 2.1 / CogVideoX FREE limited runs  (replicate.com)
  5. HuggingFace — ModelScope 1.7B     FREE always        (no key needed)

WHY ModelScope 1.7B instead of CogVideoX-5B:
  CogVideoX-5B is a ~10GB model. On HuggingFace free tier it almost always
  returns 503 "Model loading" or times out after 5 minutes.
  ModelScope 1.7B is small, loads fast, and reliably generates 2-3s clips for free.

Each provider is independently optional — app works with zero keys.
"""

import os, time, json, logging, tempfile, subprocess, shutil, requests, base64
from typing import Optional

logger = logging.getLogger(__name__)

def _get_key(env_name: str) -> str:
    """Read API key from environment or pydantic settings (handles Windows .env loading)."""
    val = os.environ.get(env_name, "")
    if not val:
        try:
            from app.config import settings
            val = getattr(settings, env_name, "") or ""
        except Exception:
            pass
    return val


# =============================================================================
# HELPERS
# =============================================================================

def _get_duration(path: str) -> float:
    try:
        probe = shutil.which("ffprobe") or "ffprobe"
        r = subprocess.run(
            [probe, "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, timeout=10,
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 18.0


def mix_audio_into_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    ffmpeg_bin: str = "ffmpeg",
) -> bool:
    if not os.path.exists(video_path) or not os.path.exists(audio_path):
        return False
    try:
        audio_dur = _get_duration(audio_path)
        result = subprocess.run([
            ffmpeg_bin, "-y",
            "-i", video_path, "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-af", f"volume=1.1,afade=t=in:d=0.3,afade=t=out:st={max(0, audio_dur - 1)}:d=0.8",
            "-shortest", "-movflags", "+faststart",
            output_path,
        ], capture_output=True, timeout=120)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        logger.error(f"Audio mix: {e}")
        return False


def _download(url: str, dest: str, timeout: int = 120) -> bool:
    try:
        r = requests.get(url, timeout=timeout, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        size = os.path.getsize(dest)
        logger.info(f"  Downloaded {size//1024}KB → {os.path.basename(dest)}")
        return size > 5000
    except Exception as e:
        logger.warning(f"Download {url[:60]}: {e}")
        return False


# =============================================================================
# 1. D-ID — Talking avatar (FREE 2-week trial, no CC)
# Sign up:  https://studio.d-id.com
# Get key:  Dashboard → API → copy "Basic xxxx..." token
# .env:     DID_API_KEY=Basic dXNlckBleGF...
# =============================================================================

def _fix_did_key(raw: str) -> str:
    """Auto-fix D-ID key: if user pasted email:password without base64-encoding, fix it."""
    raw = raw.strip()
    if not raw.startswith("Basic "):
        # No prefix at all — encode the whole thing
        return "Basic " + base64.b64encode(raw.encode()).decode()
    token = raw[6:].strip()
    # Check if token contains a raw colon (un-encoded email:password)
    try:
        decoded = base64.b64decode(token + "==").decode("utf-8", errors="ignore")
    except Exception:
        decoded = ""
    if ":" in token and ":" not in decoded:
        # Raw colon present but not in decoded — it's un-encoded
        return "Basic " + base64.b64encode(token.encode()).decode()
    return raw


def generate_with_did(script: str, output_path: str) -> Optional[str]:
    raw_key = _get_key("DID_API_KEY")
    if not raw_key:
        logger.info("DID_API_KEY not set — get free key at studio.d-id.com")
        return None

    api_key = _fix_did_key(raw_key)
    logger.info(f"D-ID: using key {api_key[:18]}...")
    headers = {"Authorization": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    BASE = "https://api.d-id.com"

    script_block = {
        "type": "text",
        "input": script,
        "provider": {"type": "microsoft", "voice_id": "en-US-GuyNeural"},
    }

    def _poll(endpoint, item_id):
        MAX_WAIT = 20   # 20 × 3s = 60 seconds max — not 6 minutes
        for attempt in range(MAX_WAIT):
            time.sleep(3)
            try:
                sr = requests.get(f"{BASE}/{endpoint}/{item_id}", headers=headers, timeout=15)
                sr.raise_for_status()
                d  = sr.json()
                st = d.get("status")
                logger.info(f"D-ID poll {attempt+1}/{MAX_WAIT}: {st}")
                if st == "done":
                    if _download(d.get("result_url", ""), output_path):
                        logger.info(f"D-ID ✓ via /{endpoint}")
                        return output_path
                    return None
                elif st in ("error", "rejected"):
                    logger.error(f"D-ID /{endpoint} error: {d.get('error')}")
                    return None
            except Exception as e:
                logger.warning(f"D-ID poll error: {e}")
        logger.warning(f"D-ID: timed out after {MAX_WAIT * 3}s — falling back to local render")
        return None

    try:
        # Attempt 1: Clips API (built-in presenters, no image URL needed)
        r = requests.post(f"{BASE}/clips", json={
            "presenter_id": "rian-lZC6MmWfC1",
            "driver_id": "uM00QS2uzl",
            "script": script_block,
            "config": {"fluent": True},
        }, headers=headers, timeout=30)

        if r.status_code in (200, 201):
            clip_id = r.json().get("id")
            if clip_id:
                result = _poll("clips", clip_id)
                if result:
                    return result

        if r.status_code == 402:
            logger.warning("D-ID: credits exhausted")
            return None

        logger.info(f"D-ID clips status {r.status_code} — trying /talks")

        # Attempt 2: /talks with a clean .jpg URL (no query params)
        for img in [
            "https://d-id-public-bucket.s3.us-east-1.amazonaws.com/alice.jpg",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/480px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        ]:
            r2 = requests.post(f"{BASE}/talks", json={
                "source_url": img,
                "script": script_block,
                "config": {"fluent": True, "stitch": True},
            }, headers=headers, timeout=30)

            if r2.status_code == 402:
                logger.warning("D-ID: credits exhausted")
                return None
            if r2.status_code in (200, 201):
                talk_id = r2.json().get("id")
                if talk_id:
                    return _poll("talks", talk_id)
            else:
                logger.warning(f"D-ID /talks {r2.status_code}: {r2.text[:150]}")

        return None
    except Exception as e:
        logger.error(f"D-ID: {e}")
        return None


# =============================================================================
# 2. HeyGen — Talking avatar (FREE 1 credit = 1 minute)
# Sign up:  https://heygen.com
# Get key:  Settings → API → Generate API Token
# .env:     HEYGEN_API_KEY=your-token
# =============================================================================
def generate_with_heygen(script: str, output_path: str) -> Optional[str]:
    api_key = _get_key("HEYGEN_API_KEY")
    if not api_key:
        return None

    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
    BASE    = "https://api.heygen.com"

    try:
        payload = {
            "video_inputs": [{
                "character": {
                    "type":         "avatar",
                    "avatar_id":    "Eric_public_pro2_20230608",
                    "avatar_style": "normal",
                },
                "voice": {
                    "type":       "text",
                    "input_text": script,
                    "voice_id":   "2d5b0e6cf36f460aa7fc47e3eee4ba54",
                    "speed":      0.95,
                },
                "background": {"type": "color", "value": "#0a0908"},
            }],
            "dimension": {"width": 720, "height": 1280},
        }

        r = requests.post(f"{BASE}/v2/video/generate", json=payload, headers=headers, timeout=30)
        if r.status_code == 400 and ("quota" in r.text.lower() or "credit" in r.text.lower()):
            logger.warning("HeyGen: free credit used")
            return None
        r.raise_for_status()
        video_id = r.json()["data"]["video_id"]

        for _ in range(180):
            time.sleep(3)
            sr = requests.get(
                f"{BASE}/v1/video_status.get?video_id={video_id}",
                headers=headers, timeout=15,
            )
            sr.raise_for_status()
            d  = sr.json()["data"]
            st = d.get("status")
            if st == "completed":
                if _download(d["video_url"], output_path):
                    logger.info("HeyGen ✓")
                    return output_path
                return None
            elif st == "failed":
                logger.error(f"HeyGen: {d.get('error')}")
                return None

        return None
    except Exception as e:
        logger.error(f"HeyGen: {e}")
        return None


# =============================================================================
# 3. Kling — Cinematic clips (FREE 66 credits/day)
# Sign up:  https://klingai.com → Developer
# Get key:  klingai.com/dev → API Key + API Secret
# .env:     KLING_API_KEY=your-key
#           KLING_API_SECRET=your-secret
# Install:  pip install PyJWT
# =============================================================================
def generate_with_kling(scenes: list, output_path: str, ffmpeg_bin: str) -> Optional[str]:
    api_key    = _get_key("KLING_API_KEY")
    api_secret = _get_key("KLING_API_SECRET")
    if not api_key or not api_secret:
        return None

    BASE = "https://api.klingai.com/v1"
    try:
        import jwt as pyjwt
        token = pyjwt.encode(
            {"iss": api_key, "exp": int(time.time()) + 1800, "nbf": int(time.time()) - 5},
            api_secret, algorithm="HS256",
        )
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except ImportError:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    tmp_dir = tempfile.mkdtemp()
    clips   = []

    try:
        for i, scene_desc in enumerate(scenes[:3]):
            logger.info(f"Kling: clip {i+1}/{min(len(scenes),3)}")
            payload = {
                "model":           "kling-v1",
                "prompt":          scene_desc,
                "negative_prompt": "blurry, low quality, watermark, text, logo",
                "cfg_scale":       0.5,
                "mode":            "std",
                "duration":        "5",
                "aspect_ratio":    "9:16",
            }

            r = requests.post(f"{BASE}/videos/text2video", json=payload,
                              headers=headers, timeout=30)
            if r.status_code in (401, 403):
                logger.warning("Kling: auth failed")
                return None
            if r.status_code == 429:
                logger.warning("Kling: daily limit reached")
                return None
            r.raise_for_status()

            task_id = r.json().get("data", {}).get("task_id")
            if not task_id:
                continue

            clip_url = None
            for _ in range(90):
                time.sleep(4)
                pr = requests.get(f"{BASE}/videos/text2video/{task_id}",
                                  headers=headers, timeout=15)
                pr.raise_for_status()
                d  = pr.json().get("data", {})
                st = d.get("task_status")
                if st == "succeed":
                    works = d.get("task_result", {}).get("videos", [])
                    if works:
                        clip_url = works[0].get("url")
                    break
                elif st in ("failed", "cancelled"):
                    break

            if clip_url:
                clip_path = os.path.join(tmp_dir, f"kling_{i}.mp4")
                if _download(clip_url, clip_path):
                    clips.append(clip_path)
                    logger.info(f"  Kling clip {i+1} ✓")

        if not clips:
            return None

        list_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        for cp in clips:
            list_file.write(f"file '{cp}'\n")
        list_file.close()

        rc = subprocess.run([
            ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
            "-i", list_file.name, "-c", "copy", output_path,
        ], capture_output=True, timeout=60).returncode

        try:
            os.unlink(list_file.name)
        except Exception:
            pass

        if rc == 0 and os.path.exists(output_path):
            logger.info("Kling ✓")
            return output_path
        return clips[0] if clips else None

    except Exception as e:
        logger.error(f"Kling: {e}")
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# =============================================================================
# 4. Replicate — Wan 2.1 / CogVideoX (FREE limited runs, no CC)
# Sign up:  https://replicate.com (GitHub login, instant)
# Get key:  Account → API Tokens
# .env:     REPLICATE_API_TOKEN=r8_your_token
# =============================================================================
def generate_with_replicate(scenes: list, output_path: str, ffmpeg_bin: str) -> Optional[str]:
    token = _get_key("REPLICATE_API_TOKEN")
    if not token:
        return None

    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    BASE    = "https://api.replicate.com/v1"

    def _run_model(owner: str, name: str, inp: dict) -> Optional[str]:
        r = requests.post(
            f"{BASE}/models/{owner}/{name}/predictions",
            headers=headers, json={"input": inp}, timeout=30,
        )
        if r.status_code == 402:
            logger.warning("Replicate: limit reached")
            return None
        r.raise_for_status()
        pred_id = r.json()["id"]

        for _ in range(150):
            time.sleep(4)
            pr = requests.get(f"{BASE}/predictions/{pred_id}", headers=headers, timeout=15)
            pr.raise_for_status()
            d  = pr.json()
            st = d["status"]
            if st == "succeeded":
                out = d.get("output")
                return out[0] if isinstance(out, list) else out
            elif st in ("failed", "canceled"):
                logger.warning(f"Replicate: {d.get('error')}")
                return None
        return None

    tmp_dir = tempfile.mkdtemp()
    clips   = []

    try:
        for i, prompt in enumerate(scenes[:3]):
            logger.info(f"Replicate: clip {i+1}")
            url = None

            # Try Wan 2.1 first (Alibaba, 2025, good quality)
            for owner, name, inp in [
                ("wavespeedai", "wan-2.1-t2v-480p", {
                    "prompt":          prompt,
                    "negative_prompt": "blurry, watermark, text",
                    "num_frames":      33,
                    "sample_steps":    30,
                }),
                # CogVideoX-5B fallback
                ("zsxkib", "cogvideox-5b", {
                    "prompt":              prompt,
                    "negative_prompt":     "blurry, low quality, watermark",
                    "num_inference_steps": 50,
                    "guidance_scale":      6.0,
                    "num_frames":          49,
                    "fps":                 8,
                }),
            ]:
                url = _run_model(owner, name, inp)
                if url:
                    break

            if url:
                clip_path = os.path.join(tmp_dir, f"rep_{i}.mp4")
                if _download(url, clip_path):
                    clips.append(clip_path)
                    logger.info(f"  Replicate clip {i+1} ✓")

        if not clips:
            return None

        list_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        for cp in clips:
            list_file.write(f"file '{cp}'\n")
        list_file.close()

        rc = subprocess.run([
            ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
            "-i", list_file.name, "-c", "copy", output_path,
        ], capture_output=True, timeout=60).returncode

        try:
            os.unlink(list_file.name)
        except Exception:
            pass

        if rc == 0 and os.path.exists(output_path):
            logger.info("Replicate ✓")
            return output_path
        return clips[0] if clips else None

    except Exception as e:
        logger.error(f"Replicate: {e}")
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# =============================================================================
# 5. HuggingFace — ModelScope 1.7B (FREE, always works, no key needed)
# =============================================================================
# WHY ModelScope 1.7B (not CogVideoX-5B):
#   CogVideoX-5B is 10GB — HF free tier almost always returns 503 or times out.
#   ModelScope 1.7B is small, loads fast, and reliably returns a short clip.
#   Quality is lower but it ACTUALLY WORKS on free tier.
#
# Optional: Sign up at huggingface.co → Settings → Access Tokens
# .env:     HF_TOKEN=hf_your_token   (higher rate limits, optional)
# =============================================================================
def generate_with_huggingface(scene_prompt: str, output_path: str) -> Optional[str]:
    hf_token = _get_key("HF_TOKEN")
    if not hf_token:
        # HuggingFace free inference API now requires authentication even for public models.
        # Sign up free at huggingface.co → Settings → Access Tokens → New token (read only)
        # Add to .env:  HF_TOKEN=hf_your_token
        logger.info("HF_TOKEN not set — skipping HuggingFace (now requires free account token)")
        return None

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type":  "application/json",
    }

    # ModelScope 1.7B — small, reliable, actually works on HF free tier
    # CogVideoX-5B is commented out — too large for free tier
    MODELS = [
        {
            "name": "ModelScope-1.7B",
            "url":  "https://api-inference.huggingface.co/models/damo-vilab/text-to-video-ms-1.7b",
            "body": {
                "inputs":      scene_prompt[:200],
                "parameters": {
                    "num_frames":          16,
                    "num_inference_steps": 25,
                    "guidance_scale":      9.0,
                },
            },
        },
    ]

    for model in MODELS:
        try:
            logger.info(f"HuggingFace [{model['name']}]: requesting…")
            r = requests.post(model["url"], headers=headers, json=model["body"], timeout=120)

            if r.status_code == 503:
                logger.info(f"  {model['name']}: model loading, waiting 20s…")
                time.sleep(20)
                r = requests.post(model["url"], headers=headers, json=model["body"], timeout=120)

            if r.status_code == 200 and len(r.content) > 5000:
                with open(output_path, "wb") as f:
                    f.write(r.content)
                logger.info(f"HuggingFace [{model['name']}] ✓")
                return output_path
            else:
                logger.warning(f"  {model['name']}: HTTP {r.status_code} — {r.text[:100]}")
        except Exception as e:
            logger.warning(f"  {model['name']}: {e}")

    return None


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================
def generate_ai_video(
    script_data: dict,
    audio_path:  str,
    output_path: str,
    ffmpeg_bin:  str = "ffmpeg",
) -> Optional[str]:
    """
    Try AI video providers in priority order.
    Returns output_path on success, None to fall through to local Pixabay renderer.

    D-ID and HeyGen are disabled — they produce avatar-on-green-screen videos
    which look worse than real Pixabay photos for social content.

    Active chain:
      1. Kling  (cinematic clips — 66 free credits/day at klingai.com/dev)
      2. Replicate (Wan 2.1 / CogVideoX — free limited runs at replicate.com)
      3. None → falls through to local PIL + Pixabay photos (always works)
    """
    output_dir = os.path.dirname(os.path.abspath(output_path))
    script     = script_data.get("script", "")
    scenes     = script_data.get("scenes", [])
    has_audio  = bool(audio_path) and os.path.exists(audio_path)

    def _finalise(raw_path: Optional[str], provider: str) -> Optional[str]:
        if not raw_path or not os.path.exists(raw_path):
            return None
        if has_audio:
            ok = mix_audio_into_video(raw_path, audio_path, output_path, ffmpeg_bin)
            if ok:
                logger.info(f"✓ {provider} + audio → {output_path}")
                return output_path
        shutil.copy(raw_path, output_path)
        logger.info(f"✓ {provider} (silent) → {output_path}")
        return output_path

    # ── Kling (cinematic clips — 66 free credits/day) ─────────────────────────
    if _get_key("KLING_API_KEY") and scenes:
        tmp = output_path.replace(".mp4", "_kling.mp4")
        result = generate_with_kling(scenes, tmp, ffmpeg_bin)
        out = _finalise(result, "Kling")
        if out:
            return out

    # ── Replicate (Wan 2.1 → CogVideoX — free limited runs) ──────────────────
    if _get_key("REPLICATE_API_TOKEN") and scenes:
        tmp = output_path.replace(".mp4", "_rep.mp4")
        result = generate_with_replicate(scenes, tmp, ffmpeg_bin)
        out = _finalise(result, "Replicate")
        if out:
            return out

    logger.info("No AI video provider configured — using local Pixabay photo render")
    return None