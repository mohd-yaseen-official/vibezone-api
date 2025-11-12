from celery import Celery
from app.core.config import settings

celery = Celery(
    "vibezone",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.app_tasks.tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=60 * 60,
)

celery.conf.beat_schedule = {}
