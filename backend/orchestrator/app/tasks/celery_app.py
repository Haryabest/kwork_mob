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
    "push-email-fallback-every-minute": {
        "task": "app.tasks.celery_app.run_push_email_fallback",
        "schedule": crontab(minute="*"),
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


@celery_app.task(name="app.tasks.celery_app.run_push_email_fallback")
def run_push_email_fallback():
    """Отложенный email-fallback: push доставлен, но не открыт за 5 мин (§3.4.3)."""
    import asyncio

    from app.core.database import async_session
    from app.core.redis import get_redis
    from app.services import push_fallback

    async def _run():
        redis = await get_redis()
        async with async_session() as db:
            result = await push_fallback.process_due(db, redis)
            await db.commit()
            return result

    return asyncio.run(_run())


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


@celery_app.task(name="app.tasks.celery_app.auto_block_inactive_members")
def auto_block_inactive_members():
    """§2.5.4: блокировка сотрудников без входа дольше auto_block_inactive_days."""
    import asyncio

    from app.tasks.company_maintenance import run_auto_block_inactive_once

    return asyncio.run(run_auto_block_inactive_once())


celery_app.conf.beat_schedule["auto-block-inactive-daily"] = {
    "task": "app.tasks.celery_app.auto_block_inactive_members",
    "schedule": crontab(hour=4, minute=0),
}


@celery_app.task(name="app.tasks.celery_app.check_storage_smart_alerts")
def check_storage_smart_alerts():
    """SMART / disk fill → Telegram (§11 / §12.4 / §22.6)."""
    import asyncio

    from app.core.database import async_session
    from app.services import storage_alerts as sa

    async def _run():
        async with async_session() as db:
            return await sa.check_and_alert(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["storage-smart-every-5-min"] = {
    "task": "app.tasks.celery_app.check_storage_smart_alerts",
    "schedule": crontab(minute="*/5"),
}


@celery_app.task(name="app.tasks.celery_app.check_write_activity")
def check_write_activity():
    """Write Activity Heartbeat: нет записи >10 мин при нагрузке (§11.16.5)."""
    import asyncio

    from app.core.database import async_session
    from app.services import write_activity as wa

    async def _run():
        async with async_session() as db:
            return await wa.check_and_alert(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["write-activity-every-2-min"] = {
    "task": "app.tasks.celery_app.check_write_activity",
    "schedule": crontab(minute="*/2"),
}


@celery_app.task(name="app.tasks.celery_app.export_audit_logs_monthly")
def export_audit_logs_monthly(year: int | None = None, month: int | None = None):
    """Ежемесячный экспорт audit/access → MinIO audit-logs (§10.7.7)."""
    import asyncio

    from app.core.database import async_session
    from app.services import audit_export as ae

    async def _run():
        async with async_session() as db:
            return await ae.export_month(db, year=year, month=month)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["audit-export-monthly"] = {
    "task": "app.tasks.celery_app.export_audit_logs_monthly",
    "schedule": crontab(day_of_month=1, hour=2, minute=15),
}


@celery_app.task(name="app.tasks.celery_app.escalate_nsfw_sla")
def escalate_nsfw_sla():
    """NSFW ручная проверка >24ч → Telegram escalate (§10.8)."""
    import asyncio

    from app.core.database import async_session
    from app.services import nsfw_sla as sla

    async def _run():
        async with async_session() as db:
            return await sla.escalate_overdue(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["nsfw-sla-every-hour"] = {
    "task": "app.tasks.celery_app.escalate_nsfw_sla",
    "schedule": crontab(minute=20),
}


@celery_app.task(name="app.tasks.celery_app.check_ops_alerts")
def check_ops_alerts():
    """Queue / all-busy / worker offline → Telegram + email (§12.4.1)."""
    import asyncio

    from app.core.database import async_session
    from app.services import ops_alerts as oa

    async def _run():
        async with async_session() as db:
            return await oa.check_and_alert(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["ops-alerts-every-minute"] = {
    "task": "app.tasks.celery_app.check_ops_alerts",
    "schedule": crontab(minute="*"),
}


@celery_app.task(name="app.tasks.celery_app.cleanup_shoot_link_photos")
def cleanup_shoot_link_photos():
    """Shoot-link photos TTL 7d если генерация не запущена (§3.15.4)."""
    import asyncio

    from app.core.database import async_session
    from app.services import shoot_cleanup as sc

    async def _run():
        async with async_session() as db:
            return await sc.cleanup_stale_photos(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["shoot-photo-cleanup-daily"] = {
    "task": "app.tasks.celery_app.cleanup_shoot_link_photos",
    "schedule": crontab(hour=3, minute=30),
}


@celery_app.task(name="app.tasks.celery_app.notify_source_expire")
def notify_source_expire():
    """Облачная копия исходников истекает через 7/3/1 день (§3.4.3 / §9.1.2)."""
    import asyncio

    from app.core.database import async_session
    from app.services import source_expire as se

    async def _run():
        async with async_session() as db:
            return await se.notify_expiring_sources(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["source-expire-daily"] = {
    "task": "app.tasks.celery_app.notify_source_expire",
    "schedule": crontab(hour=9, minute=15),
}


@celery_app.task(name="app.tasks.celery_app.sample_storage_health")
def sample_storage_health():
    """Node heartbeat timeline + disk usage sample (§11.16.3 / §23.7)."""
    import asyncio

    from app.core.database import async_session
    from app.services import disk_forecast as df
    from app.services import node_timeline as nt

    async def _run():
        async with async_session() as db:
            a = await nt.record_node_heartbeats(db)
        async with async_session() as db:
            b = await df.sample_disk_usage(db)
        return {"timeline": a, "disk": b}

    return asyncio.run(_run())


celery_app.conf.beat_schedule["storage-health-sample"] = {
    "task": "app.tasks.celery_app.sample_storage_health",
    "schedule": crontab(minute="*/5"),
}


@celery_app.task(name="app.tasks.celery_app.purge_model_trash")
def purge_model_trash():
    """Корзина >30 дней → purge (§3.3.1)."""
    import asyncio

    from app.core.database import async_session
    from app.services import model_storage as ms

    async def _run():
        async with async_session() as db:
            return await ms.purge_expired_trash(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["model-trash-purge-daily"] = {
    "task": "app.tasks.celery_app.purge_model_trash",
    "schedule": crontab(hour=4, minute=20),
}


@celery_app.task(name="app.tasks.celery_app.check_quality_alerts")
def check_quality_alerts():
    """Publication conversion + fallback segmentation (§12.4.1)."""
    import asyncio

    from app.core.database import async_session
    from app.services import quality_alerts as qa

    async def _run():
        async with async_session() as db:
            return await qa.check_and_alert(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["quality-alerts-hourly"] = {
    "task": "app.tasks.celery_app.check_quality_alerts",
    "schedule": crontab(minute=35),
}


@celery_app.task(name="app.tasks.celery_app.check_corporate_alerts")
def check_corporate_alerts():
    """Low company balance scan (§12.4.1)."""
    import asyncio

    from app.core.database import async_session
    from app.services import corporate_alerts as ca

    async def _run():
        async with async_session() as db:
            return await ca.scan_low_balances(db)

    return asyncio.run(_run())


celery_app.conf.beat_schedule["corporate-alerts-hourly"] = {
    "task": "app.tasks.celery_app.check_corporate_alerts",
    "schedule": crontab(minute=40),
}


@celery_app.task(name="app.tasks.celery_app.clear_expired_shoot_blocks")
def clear_expired_shoot_blocks():
    """Сброс shoot_link_blocked_until после истечения (§12.4.1)."""
    import asyncio

    from app.core.database import async_session
    from app.services import shoot_link_limits as sll

    async def _run():
        async with async_session() as db:
            result = await sll.clear_expired_blocks(db)
            await db.commit()
            return result

    return asyncio.run(_run())


celery_app.conf.beat_schedule["shoot-link-unblock-every-5-min"] = {
    "task": "app.tasks.celery_app.clear_expired_shoot_blocks",
    "schedule": crontab(minute="*/5"),
}


@celery_app.task(name="app.tasks.celery_app.purge_old_pending_payments")
def purge_old_pending_payments():
    """Удалить settled balance_pending_payments старше 30 дней §20.3.4."""
    import asyncio

    from app.core.database import async_session
    from app.services import pending_payments as pend

    async def _run():
        async with async_session() as db:
            deleted = await pend.purge_old_settled(db, days=30)
            await db.commit()
            return {"deleted": deleted}

    return asyncio.run(_run())


celery_app.conf.beat_schedule["pending-payments-purge-daily"] = {
    "task": "app.tasks.celery_app.purge_old_pending_payments",
    "schedule": crontab(hour=4, minute=20),
}


@celery_app.task(name="app.tasks.celery_app.poll_waiting_capture_pending")
def poll_waiting_capture_pending():
    """Re-check waiting_for_capture pending payments > 5 min §8."""
    import asyncio

    from app.core.database import async_session
    from app.services import pending_payments as pend

    async def _run():
        async with async_session() as db:
            result = await pend.refresh_stale_waiting_capture(db, min_age_minutes=5)
            await db.commit()
            return result

    from app.services.metrics import record_pending_poll

    result = asyncio.run(_run())
    record_pending_poll(result)
    return result


celery_app.conf.beat_schedule["pending-payments-poll-waiting-capture"] = {
    "task": "app.tasks.celery_app.poll_waiting_capture_pending",
    "schedule": crontab(minute="*/5"),
}

