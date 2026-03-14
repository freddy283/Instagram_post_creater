from celery import Celery
from app.config import settings

celery_app = Celery(
    "dailyquote",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.posting", "app.tasks.scheduler"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_max_retries=3,
    # Beat schedule - runs every minute to check for due posts
    beat_schedule={
        "check-due-posts": {
            "task": "app.tasks.scheduler.check_and_enqueue_posts",
            "schedule": 60.0,  # every 60 seconds
        },
    },
)
