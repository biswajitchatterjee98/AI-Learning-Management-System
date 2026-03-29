from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "ai_lms_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Ensure task registration for worker startup.
import app.tasks.jobs  # noqa: E402,F401

