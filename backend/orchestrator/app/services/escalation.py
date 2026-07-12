"""Эскалации очереди (§4.2 / §13): 30м queued→high, 20м processing→stop+requeue, 3×→refund."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import get_redis, release_task_lock
from app.models import AuditLog, Order, TaskQueue, User
from app.services.events import publish_order_status
from app.services.queue import queue_service
from app.services.worker_hub import worker_hub

logger = logging.getLogger(__name__)


async def _refund_order(db: AsyncSession, order: Order, reason: str) -> None:
    from app.services.refunds import refund_order

    await refund_order(db, order, reason=reason, prefer_card=True)


async def _bump_escalation(db: AsyncSession, row: TaskQueue) -> int:
    row.escalation_count = int(row.escalation_count or 0) + 1
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return row.escalation_count


async def _finalize_max_escalations(db: AsyncSession, row: TaskQueue, order: Order) -> None:
    """3 эскалации → refund + failed."""
    await _refund_order(db, order, "3 эскалации")
    order.status = "failed_escalation_refunded"
    row.status = "failed"
    db.add(
        AuditLog(
            company_id=order.company_id,
            user_id=order.user_id,
            action="task_escalated_refund",
            details={
                "task_id": row.task_id,
                "order_id": order.id,
                "escalation_count": row.escalation_count,
            },
        )
    )
    await db.commit()
    await publish_order_status(
        user_id=order.user_id,
        order_id=order.id,
        task_id=row.task_id,
        status=order.status,
        extra={"escalation_count": row.escalation_count, "refunded": True},
    )
    logger.warning("Task %s refunded after %s escalations", row.task_id, row.escalation_count)
    try:
        from app.services.alerts import notify_escalation

        await notify_escalation(
            task_id=row.task_id,
            stage="refund",
            escalation_count=row.escalation_count,
            order_id=order.id,
            refunded=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("escalation refund alert: %s", exc)


async def escalate_stale_queued(db: AsyncSession) -> int:
    """>30 мин в queued → priority high (начало queue:high)."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.ESCALATION_QUEUE_MINUTES)
    rows = (
        await db.scalars(
            select(TaskQueue).where(
                TaskQueue.status == "queued",
                TaskQueue.priority != "high",
                TaskQueue.created_at <= cutoff,
            )
        )
    ).all()
    n = 0
    redis = await get_redis()
    for row in rows:
        order = await db.get(Order, row.order_id)
        if not order or order.status in ("cancelled", "completed", "blocked_nsfw"):
            continue
        count = await _bump_escalation(db, row)
        db.add(
            AuditLog(
                company_id=row.company_id,
                user_id=order.user_id if order else None,
                action="task_escalated",
                details={
                    "task_id": row.task_id,
                    "stage": "queue",
                    "duration_min": settings.ESCALATION_QUEUE_MINUTES,
                    "escalation_count": count,
                },
            )
        )
        if count >= settings.ESCALATION_MAX:
            await _finalize_max_escalations(db, row, order)
            # убрать из redis
            await queue_service.remove_from_redis(row.task_id)
            n += 1
            continue

        # убрать из normal, поставить в начало high
        await queue_service.remove_from_redis(row.task_id)
        row.priority = "high"
        item = json.dumps(
            {
                "task_id": row.task_id,
                "order_id": row.order_id,
                "payload": row.payload_json or {},
            },
            ensure_ascii=False,
        )
        await redis.lpush(queue_service.QUEUE_HIGH, item)
        await db.commit()
        logger.info("Escalated queued task %s → high (count=%s)", row.task_id, count)
        try:
            from app.services.alerts import notify_escalation

            await notify_escalation(
                task_id=row.task_id,
                stage="queue",
                escalation_count=count,
                order_id=order.id if order else None,
                duration_min=settings.ESCALATION_QUEUE_MINUTES,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("escalation alert: %s", exc)
        n += 1
    return n


async def escalate_stale_processing(db: AsyncSession) -> int:
    """>20 мин processing → stop воркеру + requeue."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.ESCALATION_PROCESSING_MINUTES)
    rows = (
        await db.scalars(
            select(TaskQueue).where(
                TaskQueue.status == "processing",
                TaskQueue.processing_started_at.is_not(None),
                TaskQueue.processing_started_at <= cutoff,
            )
        )
    ).all()
    n = 0
    for row in rows:
        order = await db.get(Order, row.order_id)
        if not order:
            continue
        count = await _bump_escalation(db, row)
        db.add(
            AuditLog(
                company_id=row.company_id,
                user_id=order.user_id,
                action="task_escalated",
                details={
                    "task_id": row.task_id,
                    "stage": "processing",
                    "duration_min": settings.ESCALATION_PROCESSING_MINUTES,
                    "escalation_count": count,
                    "worker_id": row.worker_id,
                },
            )
        )

        # stop воркеру
        worker_id = row.worker_id
        conn = await worker_hub.get(worker_id) if worker_id else None
        if not conn:
            conn = await worker_hub.find_by_task(row.task_id)
        if conn:
            try:
                await conn.websocket.send_json({"type": "stop", "task_id": row.task_id})
            except Exception as exc:  # noqa: BLE001
                logger.warning("stop to %s failed: %s", conn.worker_id, exc)

        await release_task_lock(row.task_id)

        if count >= settings.ESCALATION_MAX:
            await _finalize_max_escalations(db, row, order)
            n += 1
            continue

        # requeue
        from app.services.task_lifecycle import requeue_task

        await db.commit()
        await requeue_task(row.task_id)
        logger.info("Escalated processing task %s → requeue (count=%s)", row.task_id, count)
        try:
            from app.services.alerts import notify_escalation

            await notify_escalation(
                task_id=row.task_id,
                stage="processing",
                escalation_count=count,
                order_id=order.id,
                duration_min=settings.ESCALATION_PROCESSING_MINUTES,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("escalation alert: %s", exc)
        n += 1
    return n


async def run_escalations_once() -> dict[str, int]:
    async with async_session() as db:
        q = await escalate_stale_queued(db)
        p = await escalate_stale_processing(db)
    return {"queued_escalated": q, "processing_escalated": p}
