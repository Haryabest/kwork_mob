"""Celery: фоновые задачи."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("kwork", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.beat_schedule = {
    "sync-queue-every-minute": {
        "task": "app.tasks.celery_app.sync_queue_from_postgres",
        "schedule": crontab(minute="*"),
    },
    "backup-db-every-6-hours": {
        "task": "app.tasks.celery_app.backup_postgres",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}


@celery_app.task(name="app.tasks.celery_app.sync_queue_from_postgres")
def sync_queue_from_postgres():
    """Синхронизация очереди Redis ↔ PostgreSQL."""
    import asyncio

    from app.core.database import async_session
    from app.services.queue import queue_service

    async def _run() -> int:
        async with async_session() as db:
            return await queue_service.sync_from_postgres(db)

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.celery_app.send_push_notification")
def send_push_notification(user_ids: list[int], title: str, body: str):
    """Массовая push-рассылка."""
    pass


@celery_app.task(name="app.tasks.celery_app.send_email")
def send_email(to: str, subject: str, body: str):
    """Отправка email (fallback для push)."""
    pass


@celery_app.task(name="app.tasks.celery_app.backup_postgres")
def backup_postgres():
    """Резервное копирование БД в MinIO."""
    pass
