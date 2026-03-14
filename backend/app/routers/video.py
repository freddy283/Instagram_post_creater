"""
Video router — real-time progress, per-sentence TTS sync, token-based streaming.

KEY FIXES v3:
  1. /stream and /download accept ?token= query param so <video> tags work
  2. _run() calls generate_animated_video() directly — no double TTS, no redundant AI call
  3. HuggingFace attempt uses ModelScope 1.7B (reliable free) before PIL fallback
"""
import os, threading, logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from app.database import get_db
from app.auth import get_current_user, decode_access_token
from app.models import User, Post, PostStatus
from app.services.video_generator import generate_animated_video, VIDEOS_DIR
from app.services.news_script import generate_news_script
from app.services.ai_video import generate_ai_video
from app.config import settings
from sqlalchemy.orm import Session

router   = APIRouter(prefix="/api/video", tags=["video"])
logger   = logging.getLogger(__name__)

_status:   dict = {}
_stage:    dict = {}
_progress: dict = {}
_previews: dict = {}
_running:  dict = {}


def _s(uid, stage=None, progress=None, status=None):
    if stage    is not None: _stage[uid]    = stage
    if progress is not None: _progress[uid] = progress
    if status   is not None: _status[uid]   = status
    logger.info(f"[{uid[:8]}] {_stage.get(uid)} {_progress.get(uid)}% {_status.get(uid)}")


def _run(uid: str, script_data: dict, watermark: str, out_path: str):
    """
    Clean pipeline — no double TTS, no redundant calls:
      1. Try AI video providers (D-ID, HeyGen, Kling, Replicate, HuggingFace)
      2. If all fail → generate_animated_video() which handles TTS+frames+sync internally
    """
    try:
        _s(uid, stage="script", progress=8, status="generating")

        from app.services.video_generator import _find_ffmpeg
        try:
            ff = _find_ffmpeg()
        except RuntimeError:
            ff = "ffmpeg"

        # ── Attempt 1: External AI video providers ──────────────────────────
        _s(uid, stage="ai_video", progress=15)
        ai_result = generate_ai_video(
            script_data=script_data,
            audio_path="",          # AI providers handle their own audio
            output_path=out_path,
            ffmpeg_bin=ff,
        )

        if ai_result and os.path.exists(out_path) and os.path.getsize(out_path) > 50_000:
            logger.info(f"[{uid[:8]}] AI video success")
            _s(uid, stage="done", progress=100, status="ready")
            _previews[uid] = {
                "path":   out_path,
                "topic":  script_data.get("topic", ""),
                "quote":  script_data.get("quote", ""),
                "author": script_data.get("author", ""),
                "script": script_data.get("script", ""),
            }
            return

        # ── Attempt 2: Local animated video (PIL + edge-tts + ffmpeg) ───────
        # This is the reliable fallback — per-sentence TTS sync, gradient or Pixabay BG
        logger.info(f"[{uid[:8]}] AI providers skipped/failed → local animated render")
        _s(uid, stage="tts", progress=20)

        def cb(pct):
            _progress[uid] = 20 + int(pct * 0.75)   # map 0-100 → 20-95

        generate_animated_video(
            script_data       = script_data,
            user_id           = uid,
            watermark         = watermark,
            output_path       = out_path,
            progress_callback = cb,
        )

        _s(uid, stage="done", progress=100, status="ready")
        _previews[uid] = {
            "path":   out_path,
            "topic":  script_data.get("topic", ""),
            "quote":  script_data.get("quote", ""),
            "author": script_data.get("author", ""),
            "script": script_data.get("script", ""),
        }

    except Exception as e:
        logger.error(f"[{uid[:8]}] failed: {e}", exc_info=True)
        _s(uid, stage="", progress=0, status="error")
    finally:
        _running[uid] = False


# =============================================================================
# AUTH HELPER — accepts token from header OR query param
# Browser <video> tags cannot send Authorization headers, so we allow ?token=
# =============================================================================
def _resolve_user(
    token: str | None,
    db: Session,
) -> User:
    """Validate a JWT token (from header or ?token= query param) and return user."""
    from app.models import User as UserModel
    if not token:
        raise HTTPException(401, "Not authenticated")
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid or expired token")
    user = db.query(UserModel).filter(
        UserModel.id == user_id, UserModel.is_active == True
    ).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def _real_video(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 50_000


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/generate")
def generate(current_user: User = Depends(get_current_user)):
    uid = str(current_user.id)

    if _status.get(uid) == "generating" and _running.get(uid):
        return {
            "status":   "generating",
            "progress": _progress.get(uid, 0),
            "stage":    _stage.get(uid, ""),
        }

    script_data = generate_news_script(
        theme=getattr(current_user, "video_theme", None)
    )

    brand     = current_user.ig_handle or settings.BRAND_HANDLE
    watermark = brand if brand.startswith("@") else f"@{brand}"
    out_path  = os.path.join(VIDEOS_DIR, f"preview_{uid}.mp4")

    # Clean up any stale files
    for f in [out_path, out_path + ".rendering", out_path.replace(".mp4", "_tmp.mp4")]:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass

    _s(uid, stage="script", progress=5, status="generating")
    _running[uid] = True

    threading.Thread(
        target=_run,
        args=(uid, script_data, watermark, out_path),
        daemon=True,
    ).start()

    return {
        "status":   "generating",
        "progress": 5,
        "stage":    "script",
        "topic":    script_data.get("topic"),
        "quote":    script_data.get("quote"),
        "author":   script_data.get("author"),
        "script":   script_data.get("script"),
    }


@router.get("/status")
def status(current_user: User = Depends(get_current_user)):
    uid      = str(current_user.id)
    out_path = os.path.join(VIDEOS_DIR, f"preview_{uid}.mp4")

    fsize     = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    has_video = fsize > 50_000

    st = _status.get(uid, "idle")
    if has_video and st != "ready" and not _running.get(uid, False):
        _s(uid, stage="done", progress=100, status="ready")
        st = "ready"

    p = _previews.get(uid, {})
    return {
        "status":       st,
        "stage":        _stage.get(uid, ""),
        "progress":     _progress.get(uid, 0),
        "has_video":    has_video,
        "topic":        p.get("topic"),
        "quote":        p.get("quote"),
        "author":       p.get("author"),
        "script":       p.get("script"),
        "download_url": "/api/video/download" if has_video else None,
    }


@router.get("/stream")
def stream(
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Stream the preview video.
    Accepts auth via:
      - Standard Bearer header (for API clients)
      - ?token=<jwt> query param (for <video> HTML tags which can't send headers)
    """
    if not token:
        raise HTTPException(401, "Pass ?token=<jwt> for browser video streaming")
    user = _resolve_user(token, db)

    path = os.path.join(VIDEOS_DIR, f"preview_{user.id}.mp4")
    if not _real_video(path):
        raise HTTPException(404, "No complete video yet.")

    return FileResponse(
        path,
        media_type="video/mp4",
        headers={
            "Accept-Ranges":  "bytes",
            "Cache-Control":  "no-cache",
        },
    )


@router.get("/stream-auth")
def stream_auth(current_user: User = Depends(get_current_user)):
    """Stream via standard Bearer header (for API clients / Postman)."""
    path = os.path.join(VIDEOS_DIR, f"preview_{current_user.id}.mp4")
    if not _real_video(path):
        raise HTTPException(404, "No complete video yet.")
    return FileResponse(path, media_type="video/mp4",
                        headers={"Accept-Ranges": "bytes", "Cache-Control": "no-cache"})


@router.get("/download")
def download(
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Download — accepts ?token= query param for direct <a href> links."""
    if not token:
        raise HTTPException(401, "Pass ?token=<jwt>")
    user = _resolve_user(token, db)

    path = os.path.join(VIDEOS_DIR, f"preview_{user.id}.mp4")
    if not _real_video(path):
        raise HTTPException(404, "No complete video yet.")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="aureus_daily.mp4",
        headers={"Content-Disposition": "attachment; filename=aureus_daily.mp4"},
    )


@router.get("/download-auth")
def download_auth(current_user: User = Depends(get_current_user)):
    """Download via standard Bearer header."""
    path = os.path.join(VIDEOS_DIR, f"preview_{current_user.id}.mp4")
    if not _real_video(path):
        raise HTTPException(404, "No complete video yet.")
    return FileResponse(path, media_type="video/mp4", filename="aureus_daily.mp4",
                        headers={"Content-Disposition": "attachment; filename=aureus_daily.mp4"})


@router.get("/post/{post_id}/stream")
def stream_post(
    post_id: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, db) if token else None
    if not user:
        raise HTTPException(401, "Pass ?token=<jwt>")
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user.id).first()
    if not post or not post.image_path or not os.path.exists(post.image_path):
        raise HTTPException(404, "Video not found")
    return FileResponse(post.image_path, media_type="video/mp4",
                        headers={"Accept-Ranges": "bytes"})


@router.get("/post/{post_id}/download")
def download_post(
    post_id: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, db) if token else None
    if not user:
        raise HTTPException(401, "Pass ?token=<jwt>")
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user.id).first()
    if not post or not post.image_path or not os.path.exists(post.image_path):
        raise HTTPException(404, "Video not found")
    return FileResponse(post.image_path, media_type="video/mp4",
                        filename=f"aureus_{post_id[:8]}.mp4")


@router.get("/file/{filename}")
def serve_file(filename: str):
    if not filename.endswith(".mp4") or "/" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    path = os.path.join(VIDEOS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="video/mp4")


@router.post("/post/{post_id}/acknowledge")
def ack(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(
        Post.id == post_id, Post.user_id == current_user.id
    ).first()
    if not post:
        raise HTTPException(404, "Not found")
    if post.status == PostStatus.video_ready:
        post.status = PostStatus.success
        db.commit()
    return {"ok": True, "status": post.status}