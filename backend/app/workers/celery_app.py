from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("curecompass", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_default_queue = "curecompass"
celery_app.conf.task_always_eager = settings.environment == "development"
celery_app.conf.enable_utc = True

# Import task modules so workers and beat register task names.
import app.tasks.ai_enrichment  # noqa: E402, F401
import app.tasks.digests  # noqa: E402, F401
import app.tasks.ingestion  # noqa: E402, F401

celery_app.conf.beat_schedule = {
    "digest-daily-utc": {
        "task": "digests.run_scheduled",
        "schedule": crontab(hour=7, minute=0),
        "kwargs": {"digest_type": "daily"},
    },
    "digest-weekly-utc": {
        "task": "digests.run_scheduled",
        "schedule": crontab(day_of_week=0, hour=8, minute=0),
        "kwargs": {"digest_type": "weekly"},
    },
    "digest-major-utc": {
        "task": "digests.run_scheduled",
        "schedule": crontab(hour=8, minute=30),
        "kwargs": {"digest_type": "major"},
    },
}
