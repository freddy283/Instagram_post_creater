from datetime import datetime, timedelta
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Schedule, Post, PostStatus


@celery_app.task(name="app.tasks.scheduler.check_and_enqueue_posts")
def check_and_enqueue_posts():
    """Run every minute to find schedules due and enqueue posting tasks."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Find all active schedules where next_run is overdue (within last 5 minutes)
        window_start = now - timedelta(minutes=5)
        schedules = (
            db.query(Schedule)
            .filter(
                Schedule.active == True,
                Schedule.next_run != None,
                Schedule.next_run <= now,
                Schedule.next_run >= window_start,
            )
            .all()
        )

        for schedule in schedules:
            # Idempotency: check if post already created for this slot
            existing = (
                db.query(Post)
                .filter(
                    Post.user_id == schedule.user_id,
                    Post.scheduled_for >= schedule.next_run - timedelta(minutes=5),
                    Post.scheduled_for <= schedule.next_run + timedelta(minutes=5),
                    Post.status.in_([PostStatus.queued, PostStatus.success]),
                )
                .first()
            )
            if existing:
                # Already handled; advance next_run
                _advance_next_run(schedule, db)
                continue

            if schedule.skip_next:
                # Create a skipped post record
                post = Post(
                    user_id=schedule.user_id,
                    scheduled_for=schedule.next_run,
                    status=PostStatus.skipped,
                )
                db.add(post)
                schedule.skip_next = False
                _advance_next_run(schedule, db)
                db.commit()
                continue

            # Create pending post record
            post = Post(
                user_id=schedule.user_id,
                scheduled_for=schedule.next_run,
                status=PostStatus.queued,
            )
            db.add(post)
            db.flush()  # get post.id

            # Enqueue posting task
            from app.tasks.posting import execute_post
            execute_post.apply_async(args=[post.id], countdown=0)

            _advance_next_run(schedule, db)
            db.commit()

    finally:
        db.close()


def _advance_next_run(schedule, db):
    """Move next_run forward by one day."""
    import pytz
    try:
        tz = pytz.timezone(schedule.timezone)
    except Exception:
        tz = pytz.UTC

    schedule.last_run = schedule.next_run
    next_local = schedule.next_run + timedelta(days=1)
    schedule.next_run = next_local
    schedule.updated_at = datetime.utcnow()
