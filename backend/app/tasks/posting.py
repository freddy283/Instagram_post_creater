"""
Daily video generation + optional Instagram posting.

Flow:
  1. Always: Generate quote via OpenAI (fallback to static list)
  2. Always: Render 45s cinematic video
  3. Mark post as video_ready → user gets notified in dashboard
  4. Optional: If user has auto_post_ig=True AND Instagram connected → post as Reel
"""
import asyncio
import os
import logging
from datetime import date, datetime

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Post, InstagramConnection, PostStatus, User
from app.services.video_generator import generate_quote_video, VIDEOS_DIR
from app.services.quotes import get_openai_daily_quote
from app.services.instagram import post_reel_to_instagram
from app.auth import decrypt_token
from app.config import settings

logger = logging.getLogger(__name__)

HASHTAGS = (
    "#motivation #inspiration #dailywisdom #mindset #growth "
    "#success #positivity #quoteoftheday #aureus"
)


@celery_app.task(
    name="app.tasks.posting.execute_post",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def execute_post(self, post_id: str):
    db = SessionLocal()
    post = None
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            logger.error(f"Post {post_id} not found")
            return
        if post.status == PostStatus.success:
            return

        post.status = PostStatus.queued
        db.commit()

        # ── 1. Get user preferences ──────────────────────────────────────────
        user = db.query(User).filter(User.id == post.user_id).first()
        brand_handle = (user.ig_handle or settings.BRAND_HANDLE) if user else settings.BRAND_HANDLE
        theme = (user.video_theme or settings.VIDEO_THEME) if user else settings.VIDEO_THEME
        auto_post = (user.auto_post_ig) if user else False

        # ── 2. Generate fresh quote via OpenAI ───────────────────────────────
        seed = (date.today() - date(2024, 1, 1)).days
        quote, author = get_openai_daily_quote(user_id=post.user_id, seed=seed)

        post.quote_text   = quote
        post.quote_author = author
        post.video_theme  = theme
        post.caption_text = (
            f'"{quote}"\n\n— {author}\n\n{HASHTAGS}'
        )
        db.commit()

        # ── 3. Render video ───────────────────────────────────────────────────
        os.makedirs(VIDEOS_DIR, exist_ok=True)
        output_path = os.path.join(VIDEOS_DIR, f"daily_{post.user_id}_{post_id[:8]}.mp4")

        watermark = brand_handle if brand_handle.startswith("@") else f"@{brand_handle}"
        generate_quote_video(
            quote=quote,
            author=author,
            user_id=post.user_id,
            watermark=watermark,
            output_path=output_path,
        )
        post.image_path = output_path
        post.status = PostStatus.video_ready
        db.commit()
        logger.info(f"Video ready for post {post_id}: {output_path}")

        # ── 4. Dev mode: stop here ────────────────────────────────────────────
        if settings.APP_ENV == "development" or not auto_post:
            # video_ready = user sees it in dashboard and can download
            logger.info(f"[{'DEV' if settings.APP_ENV == 'development' else 'MANUAL'}] "
                        f"Video ready, skipping auto-post for {post_id}")
            return

        # ── 5. Optional: Auto-post to Instagram ───────────────────────────────
        conn = db.query(InstagramConnection).filter(
            InstagramConnection.user_id == post.user_id,
            InstagramConnection.is_active == True,
        ).first()

        if not conn:
            logger.info(f"No IG connection for {post.user_id} — video stays in dashboard")
            return

        if conn.token_expiry and conn.token_expiry < datetime.utcnow():
            conn.is_active = False
            db.commit()
            post.error_message = "Instagram token expired — please reconnect."
            db.commit()
            logger.warning(f"IG token expired for user {post.user_id}")
            return

        access_token = decrypt_token(conn.access_token_encrypted)
        public_url   = settings.PUBLIC_URL.rstrip("/")
        video_filename = os.path.basename(output_path)
        video_url  = f"{public_url}/api/video/file/{video_filename}"

        result = asyncio.run(post_reel_to_instagram(
            ig_account_id=conn.ig_account_id,
            access_token=access_token,
            video_url=video_url,
            caption=post.caption_text,
        ))

        if result["success"]:
            post.status = PostStatus.success
            post.instagram_post_id = result["post_id"]
            post.ig_auto_posted = True
            logger.info(f"Reel auto-posted: {result['post_id']}")
        else:
            # Not a failure — video still exists, just IG didn't work
            post.error_message = f"IG post failed: {result.get('error')} — video still available"
            logger.error(f"IG post failed for {post_id}: {result.get('error')}")

        post.retry_count = str(self.request.retries)
        db.commit()

    except Exception as exc:
        logger.error(f"Post {post_id} failed (attempt {self.request.retries + 1}): {exc}")
        if post:
            post.error_message = str(exc)
            post.retry_count   = str(self.request.retries)
            if self.request.retries >= self.max_retries:
                post.status = PostStatus.failed
            else:
                post.status = PostStatus.queued
            db.commit()
        db.close()
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))
    finally:
        db.close()
