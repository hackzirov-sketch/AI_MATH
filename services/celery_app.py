from __future__ import annotations

import os

from services.bootstrap import bootstrap_runtime

bootstrap_runtime()

try:
    from celery import Celery
    from celery.schedules import crontab
except Exception:
    Celery = None
    crontab = None


def create_celery_app():
    if Celery is None:
        return None

    broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    backend_url = os.getenv("CELERY_RESULT_BACKEND", broker_url)

    app = Celery(
        "ai_math",
        broker=broker_url,
        backend=backend_url,
        include=["services.worker_tasks"],
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_ignore_result=False,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        broker_connection_retry_on_startup=True,
        result_expires=3600,
        timezone=os.getenv("APP_TIMEZONE", "Asia/Tashkent"),
    )
    if crontab is not None:
        app.conf.beat_schedule = {
            "cache-cleanup-every-10-minutes": {
                "task": "ai_math.cache.cleanup",
                "schedule": crontab(minute="*/10"),
            },
            "self-improvement-every-6-hours": {
                "task": "ai_math.self_improvement.analyze",
                "schedule": crontab(minute=0, hour="*/6"),
                "args": (200,),
            },
        }
    return app


celery_app = create_celery_app()
