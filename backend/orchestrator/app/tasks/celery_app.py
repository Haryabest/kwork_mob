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
    "escalations-every-minute": {
        "task": "app.tasks.celery_app.run_escalations",
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
    """Массовая push-рассылка (§3.4.3) + email fallback."""
    import asyncio

    from app.core.database import async_session
    from app.services import push as push_svc

    async def _run():
        async with async_session() as db:
            return await push_svc.send_to_users(db, user_ids, title, body)

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.celery_app.send_email")
def send_email(to: str, subject: str, body: str):
    """Отправка email (fallback для push)."""
    pass


@celery_app.task(name="app.tasks.celery_app.run_escalations")
def run_escalations():
    """Эскалации очереди (§4.2): 30м / 20м / 3× refund."""
    import asyncio

    from app.services.escalation import run_escalations_once

    return asyncio.run(run_escalations_once())


@celery_app.task(name="app.tasks.celery_app.backup_postgres")
def backup_postgres():
    """Резервное копирование БД в MinIO (§9)."""
    from app.services.backup import run_pg_dump_to_minio

    return run_pg_dump_to_minio()


@celery_app.task(name="app.tasks.celery_app.collect_queue_metrics")
def collect_queue_metrics():
    """Длина очередей → Prometheus/ClickHouse."""
    import asyncio

    from app.core.redis import get_redis
    from app.services.metrics import record_queue_length

    async def _run():
        redis = await get_redis()
        for name in ("queue:normal", "queue:high"):
            n = await redis.llen(name)
            record_queue_length(name, int(n or 0))
        return True

    return asyncio.run(_run())


celery_app.conf.beat_schedule["queue-metrics-every-minute"] = {
    "task": "app.tasks.celery_app.collect_queue_metrics",
    "schedule": crontab(minute="*"),
}


@celery_app.task(name="app.tasks.celery_app.run_cloud_autoscaling")
def run_cloud_autoscaling():
    """Авто-масштаб облачных GPU каждые 30с (§11.3.3)."""
    import asyncio

    from app.core.database import async_session
    from app.services.cloud_autoscaling import run_autoscaling_once

    async def _run():
        async with async_session() as db:
            return await run_autoscaling_once(db)

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.celery_app.verify_publication_links")
def verify_publication_links():
    """Проверка ссылок WB/Ozon каждые 2ч (§7.5.2)."""
    import asyncio

    from app.core.database import async_session
    from app.services.publication import verify_pending_batch

    async def _run():
        async with async_session() as db:
            return await verify_pending_batch(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["cloud-autoscaling-30s"] = {
    "task": "app.tasks.celery_app.run_cloud_autoscaling",
    "schedule": 30.0,
}
celery_app.conf.beat_schedule["publication-verify-every-2h"] = {
    "task": "app.tasks.celery_app.verify_publication_links",
    "schedule": crontab(minute=0, hour="*/2"),
}


@celery_app.task(name="app.tasks.celery_app.process_deletion_requests")
def process_deletion_requests():
    """Право на забвение: исполнить заявки после SLA 30 дней (§2.8.3)."""
    import asyncio

    from app.core.database import async_session
    from app.services.account_deletion import process_due_deletions

    async def _run():
        async with async_session() as db:
            return await process_due_deletions(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["deletion-requests-daily"] = {
    "task": "app.tasks.celery_app.process_deletion_requests",
    "schedule": crontab(hour=3, minute=15),
}


@celery_app.task(name="app.tasks.celery_app.retry_company_webhooks")
def retry_company_webhooks():
    """Retry/DLQ корпоративных webhooks (§14.5.4)."""
    import asyncio

    from app.core.database import async_session
    from app.services import company_webhooks as wh

    async def _run():
        async with async_session() as db:
            result = await wh.process_retries(db)
            await db.commit()
            return result

    return asyncio.run(_run())


celery_app.conf.beat_schedule["webhook-retries-every-minute"] = {
    "task": "app.tasks.celery_app.retry_company_webhooks",
    "schedule": crontab(minute="*"),
}
