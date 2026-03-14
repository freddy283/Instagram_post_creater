"""
Video router - real-time progress, atomic file detection.
"""
import os, threading, logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.database import get_db
from app.auth import get_current_user
from app.models import User, Post, PostStatus
from app.services.video_generator import generate_quote_video, VIDEOS_DIR
from app.services.news_script import generate_news_script
from app.services.ai_video import generate_ai_video
from app.config import settings
from sqlalchemy.orm import Session

router   = APIRouter(prefix="/api/video", tags=["video"])
logger   = logging.getLogger(__name__)

_status:   dict = {}   # uid -> idle|generating|ready|error
_stage:    dict = {}   # uid -> script|tts|frames|encoding|done
_progress: dict = {}   # uid -> 0-100
_previews: dict = {}   # uid -> {path, quote, author, topic, script}
_running:  dict = {}   # uid -> bool


def _s(uid, stage=None, progress=None, status=None):
    if stage    is not None: _stage[uid]    = stage
    if progress is not None: _progress[uid] = progress
    if status   is not None: _status[uid]   = status
    logger.info(f"[{uid[:8]}] {_stage.get(uid)} {_progress.get(uid)}% {_status.get(uid)}")


def _run(uid, script_data, watermark, out_path):
    import tempfile
    try:
        _s(uid, stage="script", progress=5, status="generating")

        quote  = script_data.get("quote", "")
        author = script_data.get("author", "")
        script = script_data.get("script", quote)

        # TTS
        _s(uid, stage="tts", progress=15)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        tts_ok = False
        try:
            from app.services.video_generator import _generate_tts
            tts_ok = _generate_tts(script, tmp.name)
        except Exception as e:
            logger.warning(f"TTS: {e}")

        # ffmpeg
        from app.services.video_generator import _find_ffmpeg
        try:
            ff = _find_ffmpeg()
        except RuntimeError:
            ff = "ffmpeg"

        # AI video attempt
        _s(uid, stage="frames", progress=25)
        ai = generate_ai_video(
            script_data=script_data,
            audio_path=tmp.name if tts_ok else "",
            output_path=out_path,
            ffmpeg_bin=ff,
        )

        # PIL fallback with real frame progress
        if not ai or not os.path.exists(out_path):
            _s(uid, stage="frames", progress=25)

            def cb(pct):
                # frame pct 0-100 -> display 25-90
                _progress[uid] = 25 + int(pct * 0.65)

            generate_quote_video(
                quote=quote, author=author, user_id=uid,
                watermark=watermark, preview=True,
                output_path=out_path, script=script,
                progress_callback=cb,
            )

        try: os.unlink(tmp.name)
        except: pass

        _s(uid, stage="done", progress=100, status="ready")
        _previews[uid] = {
            "path":   out_path,
            "quote":  quote,
            "author": author,
            "topic":  script_data.get("topic", ""),
            "script": script,
        }

    except Exception as e:
        logger.error(f"[{uid[:8]}] failed: {e}", exc_info=True)
        _s(uid, stage="", progress=0, status="error")
    finally:
        _running[uid] = False


@router.post("/generate")
def generate(current_user: User = Depends(get_current_user)):
    uid = str(current_user.id)

    if _status.get(uid) == "generating" and _running.get(uid):
        return {"status":"generating","progress":_progress.get(uid,0),"stage":_stage.get(uid,"")}

    script_data = generate_news_script(theme=getattr(current_user,"video_theme",None))

    brand     = current_user.ig_handle or settings.BRAND_HANDLE
    watermark = brand if brand.startswith("@") else f"@{brand}"
    out_path  = os.path.join(VIDEOS_DIR, f"preview_{uid}.mp4")

    # Remove all temp/stale files
    for f in [out_path, out_path.replace('.mp4','_tmp.mp4'), out_path+'.rendering', out_path+'.tmp.mp4']:
        try: os.remove(f)
        except: pass

    _s(uid, stage="script", progress=5, status="generating")
    _running[uid] = True

    threading.Thread(target=_run, args=(uid,script_data,watermark,out_path), daemon=True).start()

    return {
        "status":"generating","progress":5,"stage":"script",
        "topic": script_data.get("topic"),
        "quote": script_data.get("quote"),
        "author":script_data.get("author"),
        "script":script_data.get("script"),
    }


@router.get("/status")
def status(current_user: User = Depends(get_current_user)):
    uid      = str(current_user.id)
    out_path = os.path.join(VIDEOS_DIR, f"preview_{uid}.mp4")

    # Only count as complete if file is real (>50KB) AND no .rendering temp exists
    fsize     = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    rendering = os.path.exists(out_path + ".rendering")
    has_video = fsize > 50_000 and not rendering

    st = _status.get(uid, "idle")

    # Safety catch: thread finished but status wasn't updated
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


def _real_video(path):
    return os.path.exists(path) and os.path.getsize(path) > 50_000


@router.get("/download")
def download(current_user: User = Depends(get_current_user)):
    path = os.path.join(VIDEOS_DIR, f"preview_{current_user.id}.mp4")
    if not _real_video(path): raise HTTPException(404, "No complete video yet.")
    return FileResponse(path, media_type="video/mp4", filename="aureus_daily.mp4",
                        headers={"Content-Disposition":"attachment; filename=aureus_daily.mp4"})


@router.get("/stream")
def stream(current_user: User = Depends(get_current_user)):
    path = os.path.join(VIDEOS_DIR, f"preview_{current_user.id}.mp4")
    if not _real_video(path): raise HTTPException(404, "No complete video yet.")
    return FileResponse(path, media_type="video/mp4")


@router.get("/post/{post_id}/stream")
def stream_post(post_id:str, current_user:User=Depends(get_current_user), db:Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id==post_id, Post.user_id==current_user.id).first()
    if not post or not post.image_path or not os.path.exists(post.image_path):
        raise HTTPException(404,"Video not found")
    return FileResponse(post.image_path, media_type="video/mp4")


@router.get("/post/{post_id}/download")
def download_post(post_id:str, current_user:User=Depends(get_current_user), db:Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id==post_id, Post.user_id==current_user.id).first()
    if not post or not post.image_path or not os.path.exists(post.image_path):
        raise HTTPException(404,"Video not found")
    return FileResponse(post.image_path, media_type="video/mp4", filename=f"aureus_{post_id[:8]}.mp4")


@router.get("/file/{filename}")
def serve_file(filename:str):
    if not filename.endswith(".mp4") or "/" in filename or ".." in filename:
        raise HTTPException(400,"Invalid filename")
    path = os.path.join(VIDEOS_DIR, filename)
    if not os.path.exists(path): raise HTTPException(404,"Not found")
    return FileResponse(path, media_type="video/mp4")


@router.post("/post/{post_id}/acknowledge")
def ack(post_id:str, current_user:User=Depends(get_current_user), db:Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id==post_id, Post.user_id==current_user.id).first()
    if not post: raise HTTPException(404,"Not found")
    if post.status == PostStatus.video_ready:
        post.status = PostStatus.success
        db.commit()
    return {"ok":True,"status":post.status}