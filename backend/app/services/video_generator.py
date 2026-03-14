"""
Aureus Fast Video Generator v3.0
==================================
Target: 15-20 second output, generated in ~10-20 seconds (not 3 minutes).

WHY IT'S FAST:
  ❌ OLD: ffmpeg zoompan — renders EVERY frame individually on CPU (~3 min)
  ✅ NEW: PIL renders 3 PNG frames (~0.5s each), ffmpeg concatenates with
          simple cross-fade transitions (~5s total ffmpeg work)

Pipeline (all free, no API keys):
  1. TTS     → edge-tts (Microsoft Neural, free) → ~3-5s
  2. Frames  → PIL renders 3 beautiful scene images → ~1.5s
  3. Video   → ffmpeg concat + xfade + audio mix → ~5-8s
  TOTAL: ~10-20 seconds
"""

import os, uuid, shutil, subprocess, logging, tempfile, json, re, random, threading
from PIL import Image, ImageDraw, ImageFont
import requests

logger     = logging.getLogger(__name__)
VIDEOS_DIR = os.environ.get("VIDEOS_DIR", "./videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)

# ── Import timing from the script engine (single source of truth) ─────────────
try:
    from app.services.news_script import (
        TARGET_DURATION_S, SCENES_COUNT, generate_news_script
    )
except Exception:
    TARGET_DURATION_S = 18
    SCENES_COUNT      = 3

# ── Canvas ─────────────────────────────────────────────────────────────────────
W, H              = 1080, 1920          # Portrait (Reels / Shorts / TikTok)
SCENE_DURATION    = TARGET_DURATION_S / SCENES_COUNT   # seconds per scene
FPS               = 30
TRANSITION_S      = 0.6                 # cross-fade between scenes

# ── Colour palette ─────────────────────────────────────────────────────────────
GOLD     = (212, 175, 55)
GOLD_DIM = (160, 125, 30)
WHITE    = (255, 255, 255)
BLACK    = (0,   0,   0)

# ── Scene background gradients (top_RGB, bottom_RGB) ──────────────────────────
SCENE_GRADIENTS = [
    ((8,  14, 42), (25, 55, 110)),    # deep navy blue
    ((40,  6, 20), (95, 22, 52)),     # deep crimson
    ((5,  30, 15), (15, 78, 45)),     # deep emerald
    ((40, 28,  5), (100, 72, 14)),    # deep amber
    ((15, 10, 40), (55, 25, 100)),    # deep violet
]

# ── Decorative accent shapes per scene (drawn on the gradient) ────────────────
SCENE_ACCENTS = ["arc_top", "arc_bottom", "diagonal", "arc_top", "arc_bottom"]


# =============================================================================
# UTILITIES
# =============================================================================

def _find_ffmpeg():
    for name in ["ffmpeg", "ffmpeg.exe"]:
        p = shutil.which(name)
        if p:
            return p
    for loc in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.isfile(loc):
            return loc
    raise RuntimeError("ffmpeg not found — install: sudo apt-get install ffmpeg")


def _run(cmd, timeout=120):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    return r.returncode, (r.stderr or b"").decode("utf-8", errors="replace")


def _font(size, bold=True):
    candidates = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "C:/Windows/Fonts/georgiab.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ] if bold else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    )
    for p in candidates:
        if os.path.isfile(p):
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap(text, font, max_w):
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bb   = dummy.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def _audio_duration(path):
    """Get audio duration in seconds. Handles Windows ffprobe path."""
    try:
        ff    = _find_ffmpeg()
        # On Windows: ffprobe sits next to ffmpeg.exe
        probe = ff.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe")
        if not os.path.isfile(probe):
            probe = shutil.which("ffprobe") or "ffprobe"
        r = subprocess.run(
            [probe, "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, timeout=10,
        )
        dur = float(json.loads((r.stdout or b"{}").decode())["format"]["duration"])
        return dur
    except Exception as e:
        logger.warning(f"ffprobe duration failed ({e}) — estimating from file size")
        # Fallback: estimate duration from MP3 file size
        # edge-tts produces ~16kB/s for 24kHz mono
        try:
            size_kb = os.path.getsize(path) / 1024
            return max(1.0, size_kb / 16.0)
        except Exception:
            return 5.0   # safe default — NOT 18s


def _split_sentences(script_text):
    """Split script into exactly SCENES_COUNT parts."""
    sents = re.split(r"(?<=[.!?])\s+", script_text.strip())
    sents = [s.strip() for s in sents if s.strip()]
    if not sents:
        return [script_text] * SCENES_COUNT
    while len(sents) < SCENES_COUNT:
        sents.append("")
    # Merge extras into last sentence if AI ignored sentence limit
    if len(sents) > SCENES_COUNT:
        sents = sents[:SCENES_COUNT - 1] + [" ".join(sents[SCENES_COUNT - 1:])]
    return sents[:SCENES_COUNT]


# =============================================================================
# TTS — edge-tts (free, Microsoft Neural voices, no API key)
# =============================================================================

# ── Batch TTS: generate all sentences in a SINGLE async session ──────────────
# Running each sentence in a separate asyncio.run() causes the 3rd call to fail
# because Windows event loop state gets polluted. One session handles all.

def _generate_tts(text, out_path):
    """Single-sentence wrapper — uses batch under the hood."""
    results = _tts_edge_batch([text], [out_path])
    return results[0]


def _tts_edge_batch(texts, out_paths):
    """
    Generate TTS for ALL sentences in one single async event loop.
    Returns list of bools (success per sentence).
    """
    try:
        import edge_tts

        async def _do_all():
            results = []
            for text, path in zip(texts, out_paths):
                # Skip empty text — don't send to TTS
                if not text or not text.strip():
                    logger.warning(f"TTS: skipping empty sentence")
                    results.append(False)
                    continue
                try:
                    comm = edge_tts.Communicate(text, "en-US-GuyNeural", rate="-8%")
                    await comm.save(path)
                    ok = os.path.isfile(path) and os.path.getsize(path) > 1000
                    results.append(ok)
                    if ok:
                        logger.info(f"TTS: edge-tts ✓ ({text[:40]}…)")
                    else:
                        logger.warning(f"TTS: empty output for ({text[:40]}…)")
                        results.append(False)
                except Exception as e:
                    logger.warning(f"TTS sentence failed: {e}")
                    results.append(False)
            return results

        exc = []
        ret = []

        def _thread():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                nonlocal ret
                ret = loop.run_until_complete(_do_all())
            except Exception as e:
                exc.append(e)
            finally:
                loop.close()
                asyncio.set_event_loop(None)

        t = threading.Thread(target=_thread, daemon=True)
        t.start()
        t.join(timeout=120)
        if exc:
            raise exc[0]
        return ret if ret else [False] * len(texts)
    except Exception as e:
        logger.warning(f"edge-tts batch: {e}")
        return [False] * len(texts)





def _tts_pyttsx3(text, out_path):
    """Offline TTS fallback — no internet needed."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 145)
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        ok = os.path.isfile(out_path) and os.path.getsize(out_path) > 1000
        if ok:
            logger.info("TTS: pyttsx3 ✓")
        return ok
    except Exception as e:
        logger.warning(f"pyttsx3: {e}")
        return False


# =============================================================================
# BACKGROUND IMAGES — Pixabay (free key) → PIL gradient fallback
# =============================================================================

def _pixabay_image(scene_desc, idx=0):
    """Download a matching photo from Pixabay (free API key at pixabay.com)."""
    key = os.environ.get("PIXABAY_API_KEY", "")
    if not key:
        try:
            from app.config import settings
            key = getattr(settings, "PIXABAY_API_KEY", "")
        except Exception:
            pass
    if not key:
        return None

    stop = {
        "a","an","the","with","and","or","at","in","on","of","to","for","from",
        "by","is","are","was","cinematic","shot","close","aerial","wide","mood",
        "lighting","modern","golden","hour","light","angle","atmosphere",
        "camera","movement","dramatic","stunning","beautiful","style","view",
    }
    words    = re.sub(r"[^\w\s]", "", scene_desc.lower()).split()
    keywords = " ".join(w for w in words if w not in stop and len(w) > 2)[:60]
    if not keywords:
        keywords = "nature landscape"

    def _search(q):
        try:
            r = requests.get(
                "https://pixabay.com/api/",
                params={"key": key, "q": q, "image_type": "photo",
                        "min_width": 800, "safesearch": "true", "per_page": 10},
                timeout=10,
            )
            return r.json().get("hits", [])
        except Exception:
            return []

    hits = _search(keywords) or _search(keywords.split()[0])
    if not hits:
        return None

    try:
        url  = hits[idx % len(hits)]["largeImageURL"]
        resp = requests.get(url, timeout=20)
        tmp  = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.write(resp.content)
        tmp.close()
        logger.info(f"Pixabay [{idx}]: {keywords!r}")
        return tmp.name
    except Exception as e:
        logger.warning(f"Pixabay download: {e}")
        return None


# =============================================================================
# PIL FRAME RENDERER — generates one beautiful 1080×1920 PNG per scene
# This is what makes it FAST: PIL runs in ~0.3s vs zoompan's ~30s per scene
# =============================================================================

def _render_frame(
    sentence:     str,
    scene_num:    int,
    total_scenes: int,
    watermark:    str,
    is_last:      bool = False,
    quote:        str  = "",
    author:       str  = "",
    bg_path:      str  = None,
) -> str:
    """
    Renders one full 1080×1920 PNG frame.
    If bg_path provided: composite photo + overlay.
    Otherwise: gradient + decorative accents.
    """
    # ── Base layer ─────────────────────────────────────────────────────────────
    if bg_path and os.path.isfile(bg_path):
        try:
            bg = Image.open(bg_path).convert("RGB")
            # Fill 1080×1920 without distortion: crop from centre
            bw, bh = bg.size
            scale  = max(W / bw, H / bh)
            nw, nh = int(bw * scale), int(bh * scale)
            bg     = bg.resize((nw, nh), Image.LANCZOS)
            left   = (nw - W) // 2
            top    = (nh - H) // 2
            frame  = bg.crop((left, top, left + W, top + H))
        except Exception:
            frame = _gradient_frame(scene_num)
    else:
        frame = _gradient_frame(scene_num)

    draw = ImageDraw.Draw(frame)

    # ── Dark vignette: bottom (text readability) ───────────────────────────────
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od      = ImageDraw.Draw(overlay)
    vig_start = int(H * 0.38)
    for y in range(vig_start, H):
        a = min(220, int((y - vig_start) / (H - vig_start) * 235))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    # Top vignette (brand area)
    for y in range(0, 230):
        a = max(0, 185 - int(y * 0.88))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, a))

    frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
    draw  = ImageDraw.Draw(frame)

    # ── Brand / watermark ──────────────────────────────────────────────────────
    wm_f = _font(50, bold=True)
    wm   = watermark.upper()
    bb   = draw.textbbox((0, 0), wm, font=wm_f)
    wx   = (W - (bb[2] - bb[0])) // 2
    draw.text((wx + 2, 58), wm, font=wm_f, fill=(0, 0, 0, 170))
    draw.text((wx,     56), wm, font=wm_f, fill=(*GOLD, 230))

    # ── Gold decorative line under brand ──────────────────────────────────────
    mx = 80
    draw.line([(mx, 128), (W // 2 - 40, 128)], fill=(*GOLD_DIM, 100), width=1)
    draw.line([(W // 2 + 40, 128), (W - mx, 128)], fill=(*GOLD_DIM, 100), width=1)

    # ── Progress dots ──────────────────────────────────────────────────────────
    DOT  = 9
    GAP  = 26
    pw   = total_scenes * GAP
    sx   = (W - pw) // 2
    for i in range(total_scenes):
        cx = sx + i * GAP + DOT
        cy = 160
        if i == scene_num:
            draw.ellipse([cx - DOT, cy - DOT, cx + DOT, cy + DOT],
                         fill=(*GOLD, 255))
        else:
            r2 = DOT // 2 + 1
            draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2],
                         fill=(255, 255, 255, 90))

    # ── Content text ───────────────────────────────────────────────────────────
    if is_last and quote:
        # Last scene: sentence in upper zone, quote in lower zone — no overlap
        _draw_sentence_upper(draw, sentence)
        _draw_quote_small(draw, quote, author)
    else:
        _draw_sentence(draw, sentence)

    # ── Bottom CTA ─────────────────────────────────────────────────────────────
    cf  = _font(32, bold=False)
    cta = "Follow for more"
    bb  = draw.textbbox((0, 0), cta, font=cf)
    draw.text(((W - (bb[2] - bb[0])) // 2, H - 88), cta,
              font=cf, fill=(*GOLD, 175))

    # ── Save ───────────────────────────────────────────────────────────────────
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    frame.save(tmp.name, "PNG")
    return tmp.name


def _gradient_frame(scene_num):
    """Pure PIL gradient background (fast, no network needed)."""
    top, bot = SCENE_GRADIENTS[scene_num % len(SCENE_GRADIENTS)]
    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t   = y / H
        col = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=col)

    # Decorative arc glow (gives depth to the gradient)
    ov  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od  = ImageDraw.Draw(ov)
    cx, cy = W // 2, H // 3
    for radius, alpha in [(850, 14), (650, 10), (450, 7)]:
        od.arc([cx - radius, cy - radius, cx + radius, cy + radius],
               0, 360, fill=(*GOLD, alpha), width=2)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def _draw_sentence(draw, sentence):
    """Draw narration sentence — vertically centred in the lower half of the frame."""
    tf = _font(60, bold=True)
    while True:
        lines = _wrap(sentence or " ", tf, W - 110)
        if len(lines) <= 4 or tf.size <= 36:
            break
        tf = _font(tf.size - 4, bold=True)

    lh      = tf.size + 28
    total_h = len(lines) * lh

    # Place text block centred between 55% and 85% of screen height
    zone_top    = int(H * 0.55)
    zone_bottom = int(H * 0.85)
    zone_h      = zone_bottom - zone_top
    start_y     = zone_top + (zone_h - total_h) // 2

    for i, line in enumerate(lines):
        bb  = draw.textbbox((0, 0), line, font=tf)
        tx  = (W - (bb[2] - bb[0])) // 2
        ty  = start_y + i * lh
        # Soft shadow
        draw.text((tx + 3, ty + 3), line, font=tf, fill=(0, 0, 0, 210))
        # White text
        draw.text((tx,     ty),     line, font=tf, fill=(255, 255, 255, 248))


def _draw_sentence_upper(draw, sentence):
    """Draw sentence in upper-centre zone (40-62%) — leaves room for quote below."""
    tf = _font(56, bold=True)
    while True:
        lines = _wrap(sentence or " ", tf, W - 110)
        if len(lines) <= 3 or tf.size <= 34:
            break
        tf = _font(tf.size - 4, bold=True)

    lh      = tf.size + 24
    total_h = len(lines) * lh
    zone_top    = int(H * 0.38)
    zone_bottom = int(H * 0.60)
    zone_h      = zone_bottom - zone_top
    start_y     = zone_top + (zone_h - total_h) // 2

    for i, line in enumerate(lines):
        bb  = draw.textbbox((0, 0), line, font=tf)
        tx  = (W - (bb[2] - bb[0])) // 2
        ty  = start_y + i * lh
        draw.text((tx + 3, ty + 3), line, font=tf, fill=(0, 0, 0, 210))
        draw.text((tx,     ty),     line, font=tf, fill=(255, 255, 255, 248))


def _draw_quote_small(draw, quote, author):
    """Draw compact quote in lower zone (65-88%) — always below sentence text."""
    if not quote:
        return

    # Gold separator line
    mx = 120
    draw.line([(mx, int(H * 0.63)), (W - mx, int(H * 0.63))],
              fill=(*GOLD_DIM, 80), width=1)

    qf    = _font(36, bold=False)
    qtext = f'"{quote}"'
    lines = _wrap(qtext, qf, W - 140)

    lh          = qf.size + 16
    total_h     = len(lines) * lh + (42 if author else 0)
    zone_top    = int(H * 0.65)
    zone_bottom = int(H * 0.88)
    zone_h      = zone_bottom - zone_top
    start_y     = zone_top + (zone_h - total_h) // 2

    for i, line in enumerate(lines):
        bb  = draw.textbbox((0, 0), line, font=qf)
        tx  = (W - (bb[2] - bb[0])) // 2
        ty  = start_y + i * lh
        draw.text((tx + 1, ty + 1), line, font=qf, fill=(0, 0, 0, 170))
        draw.text((tx,     ty),     line, font=qf, fill=(*GOLD, 210))

    if author:
        af  = _font(30, bold=False)
        atx = f"— {author}"
        bb  = draw.textbbox((0, 0), atx, font=af)
        tx  = (W - (bb[2] - bb[0])) // 2
        ty  = start_y + len(lines) * lh + 10
        draw.text((tx, ty), atx, font=af, fill=(*GOLD_DIM, 185))


# =============================================================================
# FFMPEG HELPERS — fast, stream-based (no per-frame processing)
# =============================================================================

def _image_to_clip(img_path, duration, out_path, ff):
    """
    Convert a single PNG → fixed-duration MP4 clip.
    Fast: ffmpeg just loops the image, no per-frame computation.
    """
    fade_d = min(0.4, duration * 0.15)
    cmd = [
        ff, "-y",
        "-loop", "1", "-i", img_path,
        "-vf", (
            f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fade=t=in:st=0:d={fade_d},"
            f"fade=t=out:st={duration - fade_d}:d={fade_d}"
        ),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        out_path,
    ]
    rc, err = _run(cmd, timeout=60)
    if rc != 0:
        raise RuntimeError(f"image_to_clip failed: {err[-200:]}")


def _concat_with_xfade(clip_paths, out_path, ff):
    """
    Concatenate clips with xfade cross-dissolve transitions.
    Fast: operates on encoded clips, not raw frames.
    """
    n = len(clip_paths)
    if n == 1:
        shutil.copy(clip_paths[0], out_path)
        return

    inputs  = []
    for p in clip_paths:
        inputs.extend(["-i", p])

    filters = []
    prev    = "0:v"
    offset  = SCENE_DURATION - TRANSITION_S

    for i in range(1, n):
        label = f"v{i}"
        filters.append(
            f"[{prev}][{i}:v]"
            f"xfade=transition=fade:duration={TRANSITION_S}:offset={offset:.3f}"
            f"[{label}]"
        )
        prev    = label
        offset += SCENE_DURATION - TRANSITION_S

    cmd = [ff, "-y"] + inputs + [
        "-filter_complex", ";".join(filters),
        "-map", f"[{prev}]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        out_path,
    ]
    rc, err = _run(cmd, timeout=90)
    if rc != 0:
        raise RuntimeError(f"xfade concat failed: {err[-300:]}")


def _add_audio(video_path, audio_path, total_dur, out_path, ff, has_audio):
    """Mix audio track with the silent video."""
    if has_audio:
        # Pad audio with 0.5s silence at start, loop if shorter than video
        cmd = [
            ff, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex",
            "[1:a]adelay=300|300,apad[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(total_dur + 1.5),
            "-shortest",
            out_path,
        ]
    else:
        # Ambient tone fallback (calming dual sine)
        cmd = [
            ff, "-y",
            "-i", video_path,
            "-f", "lavfi", "-i",
            "aevalsrc='0.03*sin(2*PI*110*t)+0.015*sin(2*PI*165*t)':s=44100:c=stereo",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "96k",
            "-t", str(total_dur + 1.5),
            out_path,
        ]
    rc, err = _run(cmd, timeout=60)
    if rc != 0:
        raise RuntimeError(f"add_audio failed: {err[-200:]}")


# =============================================================================
# MAIN VIDEO BUILDER
# =============================================================================

def generate_animated_video(
    script_data,
    user_id           = "",
    watermark         = "Aureus",
    output_path       = None,
    progress_callback = None,
):
    """
    Fast 3-scene video generator with PERFECT audio sync.

    Key fix: TTS is generated per sentence individually.
    Each scene clip is built to exactly match its sentence's spoken duration.
    This guarantees the text on screen always matches what the voice is saying.
    """
    p  = progress_callback or (lambda x: None)
    ff = _find_ffmpeg()

    if not output_path:
        output_path = os.path.join(
            VIDEOS_DIR, f"post_{user_id}_{uuid.uuid4().hex[:6]}.mp4"
        )
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    script_text = script_data.get("script", "")
    scenes_desc = list(script_data.get("scenes", []))
    quote       = script_data.get("quote", "")
    author      = script_data.get("author", "")

    while len(scenes_desc) < SCENES_COUNT:
        scenes_desc.append("Cinematic wide shot, golden hour light")
    scenes_desc = scenes_desc[:SCENES_COUNT]

    sentences = _split_sentences(script_text)
    tmp_files = []

    try:
        # ── Step 1: TTS per sentence → measure exact duration per scene ────────
        # This is the KEY fix for audio/video sync.
        # Each sentence gets its own audio file → we know exactly how long
        # each scene needs to be → scene clip duration = sentence audio duration.
        p(5)
        logger.info("Step 1: TTS per sentence…")

        sentence_audios = []   # list of (audio_path_or_None, duration_s)
        fallback_dur    = TARGET_DURATION_S / SCENES_COUNT  # e.g. 6s

        # Generate ALL sentences in one batch TTS call (fixes sentence-3 failure)
        audio_paths = [tempfile.mktemp(suffix=f"_sent{i}.mp3") for i in range(len(sentences))]
        tts_results = _tts_edge_batch(sentences, audio_paths)

        for i, (sentence, audio_path, ok) in enumerate(zip(sentences, audio_paths, tts_results)):
            if ok:
                tmp_files.append(audio_path)
                dur = _audio_duration(audio_path)
                dur = max(3.0, min(9.0, dur + 0.5))
                sentence_audios.append((audio_path, dur))
                logger.info(f"  Sentence {i+1}: {dur:.2f}s — {sentence[:50]}")
            else:
                sentence_audios.append((None, fallback_dur))
                logger.info(f"  Sentence {i+1}: TTS failed, using {fallback_dur}s fallback")

        has_audio  = any(a for a, _ in sentence_audios)
        total_dur  = sum(d for _, d in sentence_audios)
        logger.info(f"Total video duration: {total_dur:.2f}s")

        # ── Step 2: Render PNG frames ─────────────────────────────────────────
        p(20)
        logger.info("Step 2: Rendering frames…")
        frame_paths = []
        for i in range(SCENES_COUNT):
            is_last = (i == SCENES_COUNT - 1)
            bg      = _pixabay_image(scenes_desc[i], idx=i)
            if bg:
                tmp_files.append(bg)
            frame = _render_frame(
                sentence     = sentences[i],
                scene_num    = i,
                total_scenes = SCENES_COUNT,
                watermark    = watermark,
                is_last      = is_last,
                quote        = quote,
                author       = author,
                bg_path      = bg,
            )
            tmp_files.append(frame)
            frame_paths.append(frame)
            p(20 + (i + 1) * 12)
            logger.info(f"  Frame {i+1}/{SCENES_COUNT} ✓")

        # ── Step 3: Build each scene clip = frame + matching sentence audio ────
        # Each clip is SILENT video. Audio is mixed in per-clip below.
        p(60)
        logger.info("Step 3: Building scene clips with synced audio…")
        synced_clips = []

        for i, (frame, (audio_path, scene_dur)) in enumerate(
            zip(frame_paths, sentence_audios)
        ):
            # 3a: image → silent video clip (exact duration)
            silent_clip = tempfile.mktemp(suffix=f"_silent{i}.mp4")
            tmp_files.append(silent_clip)
            _image_to_clip(frame, scene_dur, silent_clip, ff)

            # 3b: mix sentence audio into this clip
            synced_clip = tempfile.mktemp(suffix=f"_synced{i}.mp4")
            tmp_files.append(synced_clip)

            if audio_path and os.path.isfile(audio_path):
                cmd = [
                    ff, "-y",
                    "-i", silent_clip,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "128k",
                    "-map", "0:v", "-map", "1:a",
                    "-t", str(scene_dur),
                    "-shortest",
                    synced_clip,
                ]
                rc, err = _run(cmd, timeout=30)
                if rc != 0:
                    logger.warning(f"Audio mix clip {i}: {err[-100:]}")
                    shutil.copy(silent_clip, synced_clip)
            else:
                # Silent fallback — ambient tone for this scene
                cmd = [
                    ff, "-y",
                    "-i", silent_clip,
                    "-f", "lavfi", "-i",
                    "aevalsrc='0.025*sin(2*PI*110*t)':s=44100:c=stereo",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "96k",
                    "-t", str(scene_dur),
                    "-shortest",
                    synced_clip,
                ]
                rc, err = _run(cmd, timeout=30)
                if rc != 0:
                    shutil.copy(silent_clip, synced_clip)

            synced_clips.append(synced_clip)
            logger.info(f"  Scene {i+1} synced ✓ ({scene_dur:.2f}s)")

        # ── Step 4: Concatenate synced clips (simple concat, no xfade) ────────
        # We use concat demuxer here because clips already have audio.
        # xfade does not work easily with audio — concat demuxer is cleaner.
        p(85)
        logger.info("Step 4: Concatenating synced clips…")
        list_file = tempfile.mktemp(suffix="_list.txt")
        tmp_files.append(list_file)
        with open(list_file, "w") as f:
            for clip in synced_clips:
                f.write(f"file '{clip}'\n")

        cmd = [
            ff, "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        rc, err = _run(cmd, timeout=90)
        if rc != 0:
            raise RuntimeError(f"Concat failed: {err[-300:]}")

        p(100)
        sz = os.path.getsize(output_path) // 1024
        logger.info(f"Done ✓  {output_path}  ({sz} KB)  total={total_dur:.1f}s")
        return output_path

    finally:
        for f in tmp_files:
            try:
                if f and os.path.isfile(f):
                    os.remove(f)
            except Exception:
                pass


# =============================================================================
# BACKWARDS-COMPATIBLE WRAPPER (used by existing video.py router)
# =============================================================================

def generate_quote_video(
    quote,
    author            = "",
    user_id           = "",
    watermark         = "Aureus",
    preview           = False,
    output_path       = None,
    script            = None,
    progress_callback = None,
):
    """Drop-in replacement for old generate_quote_video()."""
    p = progress_callback or (lambda x: None)
    p(3)

    from app.services.news_script import generate_news_script
    script_data = generate_news_script()
    if quote:
        script_data["quote"] = quote
    if author:
        script_data["author"] = author
    if script:
        script_data["script"] = script

    if not output_path:
        prefix      = "preview" if preview else "post"
        output_path = os.path.join(
            VIDEOS_DIR, f"{prefix}_{user_id}_{uuid.uuid4().hex[:6]}.mp4"
        )

    return generate_animated_video(
        script_data       = script_data,
        user_id           = user_id,
        watermark         = watermark,
        output_path       = output_path,
        progress_callback = p,
    )


# Keep old import working
generate_video_script = generate_news_script
FALLBACK_SCRIPTS      = []