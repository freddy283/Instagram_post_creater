"""
AI Video Generation — Free-First Approach
==========================================
Tries free providers in order of quality:

  1.  D-ID         — Talking-head avatar (FREE 2-week trial, no CC needed)
  2.  HeyGen       — Talking-head avatar (FREE 1 credit = 1 min, no CC needed)
  3.  Replicate    — Scene clips via Zeroscope/AnimateDiff (FREE limited runs)
  4.  Hugging Face — ModelScope text-to-video (COMPLETELY FREE, lower quality)
  5.  PIL fallback — Always works (gold text animation)

Setup: just set the key for whichever service you sign up for.
Full instructions below each provider.
"""

import os, time, json, logging, tempfile, requests, shutil, base64
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  D-ID  — Talking Head Avatar  (FREE TRIAL)
# ─────────────────────────────────────────────────────────────────────────────
# HOW TO GET FREE ACCESS (5 minutes):
#   1. Go to https://studio.d-id.com  →  Sign Up (no credit card)
#   2. You get a 2-week free trial with 20 credits (~5 min of video)
#   3. Dashboard → top-right menu → API  →  copy your Basic auth key
#      It looks like:  Basic dXNlckBleGFtcGxlLmNvbTpwYXNzd29yZA==
#   4. Add to backend/.env:   DID_API_KEY=Basic dXNlck...
#
# What you get: A real-looking photorealistic avatar person on screen,
# reading your script with natural lip-sync and head movements.
# Output: MP4, up to 5 min, 1280x1280 (square) or any ratio.
# Free trial watermark: full-screen overlay (upgrade $5.9/mo to remove).
# ─────────────────────────────────────────────────────────────────────────────
def generate_with_did(script: str, output_path: str) -> Optional[str]:
    api_key = os.environ.get("DID_API_KEY", "")
    if not api_key:
        logger.info("DID_API_KEY not set — sign up free at studio.d-id.com")
        return None

    headers = {
        "Authorization": api_key,   # already includes "Basic "
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    BASE = "https://api.d-id.com"

    try:
        # Use a publicly available professional presenter image
        # D-ID has built-in presenters — we use their stock avatar
        payload = {
            "source_url": "https://create-images-results.d-id.com/DefaultPresenters/Noelle_f/image.jpeg",
            "script": {
                "type": "text",
                "input": script,
                "provider": {
                    "type": "microsoft",
                    "voice_id": "en-US-GuyNeural",   # Professional male voice
                    "voice_config": {"style": "Newscast"},
                },
            },
            "config": {
                "fluent": True,
                "pad_audio": 0.0,
                "stitch": True,
            },
        }

        # Submit
        r = requests.post(f"{BASE}/talks", json=payload, headers=headers, timeout=30)
        if r.status_code == 402:
            logger.warning("D-ID: No credits remaining on free trial")
            return None
        r.raise_for_status()
        talk_id = r.json()["id"]
        logger.info(f"D-ID talk submitted: {talk_id}")

        # Poll
        for _ in range(120):   # up to 4 min
            time.sleep(3)
            status_r = requests.get(f"{BASE}/talks/{talk_id}", headers=headers, timeout=15)
            status_r.raise_for_status()
            data = status_r.json()
            st = data.get("status")
            if st == "done":
                video_url = data.get("result_url")
                if not video_url:
                    return None
                dl = requests.get(video_url, timeout=120)
                dl.raise_for_status()
                with open(output_path, "wb") as f:
                    f.write(dl.content)
                logger.info(f"✓ D-ID video saved: {output_path}")
                return output_path
            elif st in ("error", "rejected"):
                logger.error(f"D-ID error: {data.get('error')}")
                return None
            logger.debug(f"D-ID status: {st}")

        logger.error("D-ID: timed out")
        return None
    except Exception as e:
        logger.error(f"D-ID failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 2.  HeyGen  — Talking Head Avatar  (FREE 1 credit = 1 minute)
# ─────────────────────────────────────────────────────────────────────────────
# HOW TO GET FREE ACCESS (5 minutes):
#   1. Go to https://heygen.com  →  Sign Up (no credit card)
#   2. You get 1 free credit (= 1 minute of video)
#   3. Settings → API → Generate API Token
#   4. Add to backend/.env:   HEYGEN_API_KEY=your-token
# ─────────────────────────────────────────────────────────────────────────────
def generate_with_heygen(script: str, output_path: str) -> Optional[str]:
    api_key = os.environ.get("HEYGEN_API_KEY", "")
    if not api_key:
        logger.info("HEYGEN_API_KEY not set — sign up free at heygen.com")
        return None

    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
    BASE = "https://api.heygen.com"

    try:
        payload = {
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": "Eric_public_pro2_20230608",
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": "2d5b0e6cf36f460aa7fc47e3eee4ba54",
                    "speed": 0.95,
                },
                "background": {"type": "color", "value": "#0a0908"},
            }],
            "dimension": {"width": 720, "height": 1280},  # 9:16 vertical
            "test": False,
        }

        r = requests.post(f"{BASE}/v2/video/generate", json=payload, headers=headers, timeout=30)
        if r.status_code == 400:
            err = r.json()
            if "quota" in str(err).lower() or "credit" in str(err).lower():
                logger.warning("HeyGen: free credit already used")
                return None
        r.raise_for_status()
        video_id = r.json()["data"]["video_id"]

        for _ in range(180):
            time.sleep(3)
            st_r = requests.get(f"{BASE}/v1/video_status.get?video_id={video_id}", headers=headers, timeout=15)
            st_r.raise_for_status()
            d = st_r.json()["data"]
            st = d.get("status")
            if st == "completed":
                url = d["video_url"]
                dl = requests.get(url, timeout=120)
                dl.raise_for_status()
                with open(output_path, "wb") as f:
                    f.write(dl.content)
                logger.info(f"✓ HeyGen video saved: {output_path}")
                return output_path
            elif st == "failed":
                logger.error(f"HeyGen failed: {d.get('error')}")
                return None
        return None
    except Exception as e:
        logger.error(f"HeyGen failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Replicate  — Scene clips (FREE limited runs, no CC)
# ─────────────────────────────────────────────────────────────────────────────
# HOW TO GET FREE ACCESS (2 minutes):
#   1. Go to https://replicate.com  →  Sign Up with GitHub
#   2. Free tier: limited runs on open-source models (no CC needed)
#   3. Account → API Tokens  →  copy token
#   4. Add to backend/.env:   REPLICATE_API_TOKEN=r8_your_token
#
# Models used (all free-tier eligible):
#   - anotherjesse/zeroscope-v2-xl  (best free scene quality)
#   - lucataco/animate-diff          (smooth animations)
# ─────────────────────────────────────────────────────────────────────────────
def generate_with_replicate(scenes: list, output_dir: str, ffmpeg_bin: str) -> Optional[str]:
    api_token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not api_token:
        logger.info("REPLICATE_API_TOKEN not set — sign up free at replicate.com")
        return None

    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json",
    }
    BASE = "https://api.replicate.com/v1"

    def run_prediction(model: str, input_data: dict) -> Optional[str]:
        """Submit + poll a Replicate prediction. Returns URL of output video."""
        r = requests.post(f"{BASE}/predictions", headers=headers,
                          json={"version": model, "input": input_data}, timeout=30)
        if r.status_code == 402:
            logger.warning("Replicate: free run limit reached — add $5 credit")
            return None
        r.raise_for_status()
        pred_id = r.json()["id"]

        for _ in range(120):
            time.sleep(4)
            pr = requests.get(f"{BASE}/predictions/{pred_id}", headers=headers, timeout=15)
            pr.raise_for_status()
            d = pr.json()
            st = d["status"]
            if st == "succeeded":
                out = d.get("output")
                if isinstance(out, list): return out[0]
                return out
            elif st in ("failed", "canceled"):
                logger.error(f"Replicate prediction failed: {d.get('error')}")
                return None
        return None

    # Use Zeroscope XL — best free open-source text-to-video on Replicate
    # Model version: anotherjesse/zeroscope-v2-xl (latest)
    ZEROSCOPE_VERSION = "9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351"

    clips = []
    for i, scene_prompt in enumerate(scenes[:4]):  # max 4 clips
        logger.info(f"Replicate: generating clip {i+1}/{min(len(scenes),4)}")
        url = run_prediction(ZEROSCOPE_VERSION, {
            "prompt": scene_prompt,
            "negative_prompt": "blurry, low quality, distorted, text, watermark",
            "num_frames": 24,      # ~3-4 seconds at 8fps
            "num_inference_steps": 40,
            "guidance_scale": 7.5,
            "width": 576,
            "height": 320,         # landscape (will be cropped to 9:16 later)
            "fps": 8,
        })
        if not url:
            continue
        clip_path = os.path.join(output_dir, f"replicate_clip_{i}.mp4")
        dl = requests.get(url, timeout=120)
        dl.raise_for_status()
        with open(clip_path, "wb") as f:
            f.write(dl.content)
        clips.append(clip_path)
        logger.info(f"  Clip {i+1} downloaded")

    if not clips:
        return None

    # Concatenate clips
    output_path = os.path.join(output_dir, "replicate_combined.mp4")
    concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    for cp in clips:
        concat_file.write(f"file '{os.path.abspath(cp)}'\n")
    concat_file.close()

    try:
        import subprocess
        result = subprocess.run([
            ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file.name, "-c", "copy", output_path
        ], capture_output=True, timeout=60)
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info(f"✓ Replicate clips combined: {output_path}")
            return output_path
    except Exception as e:
        logger.error(f"Replicate concat failed: {e}")
    finally:
        try: os.unlink(concat_file.name)
        except: pass

    # If concat failed, return first clip
    return clips[0] if clips else None


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Hugging Face Inference API  — COMPLETELY FREE, no sign-up needed
# ─────────────────────────────────────────────────────────────────────────────
# The Hugging Face free inference API lets you call hosted models.
# For VIDEO specifically: damo-vilab/text-to-video-ms-1.7b
# Quality: lower than commercial tools, but genuinely free.
#
# Optional: Sign up at huggingface.co for higher rate limits.
# Add to backend/.env:   HF_TOKEN=hf_your_token   (optional, higher limits)
# ─────────────────────────────────────────────────────────────────────────────
def generate_with_huggingface(scene_prompt: str, output_dir: str) -> Optional[str]:
    # Works without a token (rate limited) or with free HF token
    hf_token = os.environ.get("HF_TOKEN", "")
    headers = {"Content-Type": "application/json"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    try:
        # ModelScope text-to-video 1.7B — free hosted inference
        url = "https://router.huggingface.co/hf-inference/models/damo-vilab/text-to-video-ms-1.7b"
        payload = {
            "inputs": scene_prompt,
            "parameters": {
                "num_frames": 16,
                "num_inference_steps": 25,
                "guidance_scale": 9.0,
            }
        }

        logger.info("HuggingFace: requesting video generation (free)...")
        r = requests.post(url, headers=headers, json=payload, timeout=300)

        if r.status_code == 503:
            # Model loading — retry once
            logger.info("HF model loading, retrying in 30s...")
            time.sleep(30)
            r = requests.post(url, headers=headers, json=payload, timeout=300)

        if r.status_code == 200 and len(r.content) > 1000:
            out_path = os.path.join(output_dir, "hf_video.mp4")
            with open(out_path, "wb") as f:
                f.write(r.content)
            logger.info(f"✓ HuggingFace video saved: {out_path}")
            return out_path
        else:
            logger.warning(f"HF returned {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"HuggingFace inference failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Mix narration audio into a video file
# ─────────────────────────────────────────────────────────────────────────────
def mix_audio_into_video(video_path: str, audio_path: str, output_path: str,
                          ffmpeg_bin: str = "ffmpeg") -> bool:
    if not os.path.exists(video_path) or not os.path.exists(audio_path):
        return False
    try:
        import subprocess
        result = subprocess.run([
            ffmpeg_bin, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-af", "volume=1.2,afade=t=in:d=0.4,afade=t=out:st={}:d=1".format(
                max(0, _get_duration(audio_path, ffmpeg_bin) - 1)
            ),
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ], capture_output=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Audio mix failed: {e}")
        return False


def _get_duration(path: str, ffmpeg_bin: str = "ffmpeg") -> float:
    try:
        import subprocess, json as _json
        probe = ffmpeg_bin.replace("ffmpeg", "ffprobe")
        if not os.path.exists(probe): probe = "ffprobe"
        r = subprocess.run([probe, "-v", "quiet", "-print_format", "json",
                            "-show_format", path], capture_output=True, text=True, timeout=10)
        return float(_json.loads(r.stdout)["format"]["duration"])
    except:
        return 20.0


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────
def generate_ai_video(script_data: dict, audio_path: str, output_path: str,
                       ffmpeg_bin: str = "ffmpeg") -> Optional[str]:
    """
    Try free AI video providers in priority order.
    Returns final output_path on success, None if all fail.
    """
    output_dir = os.path.dirname(os.path.abspath(output_path))
    script     = script_data.get("script", "")
    scenes     = script_data.get("scenes", [])
    # Use first scene as HF prompt if no scenes
    hf_prompt  = scenes[0] if scenes else script_data.get("topic", "motivational video cinematic")

    has_audio = os.path.exists(audio_path)

    # ── 1. D-ID (free trial, best quality talking head) ───────────────────
    if os.environ.get("DID_API_KEY"):
        tmp_out = output_path.replace(".mp4", "_did.mp4")
        result = generate_with_did(script, tmp_out)
        if result and os.path.exists(result):
            if has_audio:
                ok = mix_audio_into_video(result, audio_path, output_path, ffmpeg_bin)
                if ok: return output_path
            shutil.copy(result, output_path)
            return output_path

    # ── 2. HeyGen (1 free video, best quality) ────────────────────────────
    if os.environ.get("HEYGEN_API_KEY"):
        tmp_out = output_path.replace(".mp4", "_hg.mp4")
        result = generate_with_heygen(script, tmp_out)
        if result and os.path.exists(result):
            if has_audio:
                ok = mix_audio_into_video(result, audio_path, output_path, ffmpeg_bin)
                if ok: return output_path
            shutil.copy(result, output_path)
            return output_path

    # ── 3. Replicate (free limited runs) ──────────────────────────────────
    if os.environ.get("REPLICATE_API_TOKEN") and scenes:
        result = generate_with_replicate(scenes, output_dir, ffmpeg_bin)
        if result and os.path.exists(result):
            final = output_path
            if has_audio:
                ok = mix_audio_into_video(result, audio_path, final, ffmpeg_bin)
                if ok: return final
            shutil.copy(result, final)
            return final

    # ── 4. Hugging Face (completely free, lower quality) ──────────────────
    if True:   # always try HF as it's free with no setup
        result = generate_with_huggingface(hf_prompt, output_dir)
        if result and os.path.exists(result):
            final = output_path
            if has_audio:
                ok = mix_audio_into_video(result, audio_path, final, ffmpeg_bin)
                if ok: return final
            shutil.copy(result, final)
            return final

    logger.info("All AI providers failed — using PIL fallback")
    return None
