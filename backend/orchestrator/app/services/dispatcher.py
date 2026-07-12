"""Фоновый dispatch: idle-воркер ← Redis queue + grace requeue."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import acquire_task_lock, release_task_lock
from app.models import Order, TaskQueue, WorkerNode
from app.services.queue import queue_service
from app.services.task_lifecycle import mark_processing, requeue_task
from app.services.worker_hub import worker_hub

logger = logging.getLogger(__name__)

_dispatch_task: asyncio.Task | None = None
_grace_task: asyncio.Task | None = None
_escalation_task: asyncio.Task | None = None
_stop = asyncio.Event()


async def _assign_once() -> bool:
    worker = await worker_hub.pick_idle()
    if not worker:
        return False

    item = await queue_service.dequeue()
    if not item:
        return False

    task_id = item["task_id"]
    payload = item.get("payload") or {}

    async with async_session() as db:
        row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
        order = await db.get(Order, item.get("order_id") or (row.order_id if row else 0))
        if not row or row.status not in ("queued", "failed"):
            return True
        if not order or order.status in ("cancelled", "completed", "failed", "blocked_nsfw"):
            row.status = "cancelled" if order and order.status == "cancelled" else row.status
            await db.commit()
            return True
        if order.status == "awaiting_payment":
            await queue_service.enqueue(
                db,
                task_id=task_id,
                order_id=order.id,
                company_id=order.company_id,
                payload=payload or row.payload_json or {},
                priority=row.priority,
            )
            await db.commit()
            return True

        locked = await acquire_task_lock(task_id, worker.worker_id, ttl=120)
        if not locked:
            await queue_service.enqueue(
                db,
                task_id=task_id,
                order_id=order.id,
                company_id=order.company_id,
                payload=payload or row.payload_json or {},
                priority=row.priority,
            )
            await db.commit()
            return True

        await mark_processing(db, task_id, worker.worker_id)
        full_payload = {**(row.payload_json or {}), **payload}

    await worker_hub.set_busy(worker.worker_id, task_id)
    try:
        await worker.websocket.send_json(
            {
                "type": "task",
                "task_id": task_id,
                "order_id": item.get("order_id"),
                "payload": full_payload,
            }
        )
        logger.info("Dispatched task %s → worker %s", task_id, worker.worker_id)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send task %s to %s", task_id, worker.worker_id)
        await worker_hub.set_idle(worker.worker_id)
        await requeue_task(task_id)
        return True


async def _grace_once() -> None:
    """§4/§13: heartbeat timeout + grace_period → requeue."""
    base = float(settings.HEARTBEAT_TIMEOUT_SECONDS + settings.GRACE_PERIOD_SECONDS)
    stale = await worker_hub.stale_busy(base)
    for w in stale:
        grace = settings.GRACE_PERIOD_SECONDS
        async with async_session() as db:
            node = await db.get(WorkerNode, w.worker_id)
            if node and node.grace_period:
                grace = int(node.grace_period)
        timeout = settings.HEARTBEAT_TIMEOUT_SECONDS + grace
        age_sec = (datetime.now(timezone.utc) - w.last_heartbeat).total_seconds()
        if age_sec < timeout:
            continue
        task_id = w.current_task_id
        if not task_id:
            continue
        logger.warning(
            "Grace requeue task=%s worker=%s age=%.0fs (limit=%ss)",
            task_id,
            w.worker_id,
            age_sec,
            timeout,
        )
        await release_task_lock(task_id)
        await requeue_task(task_id)
        await worker_hub.set_idle(w.worker_id)


async def dispatch_loop() -> None:
    logger.info("Dispatcher started")
    while not _stop.is_set():
        try:
            assigned = await _assign_once()
            if not assigned:
                try:
                    await asyncio.wait_for(_stop.wait(), timeout=1.0)
                except TimeoutError:
                    pass
        except Exception:  # noqa: BLE001
            logger.exception("Dispatcher error")
            await asyncio.sleep(2)
    logger.info("Dispatcher stopped")


async def grace_loop() -> None:
    logger.info("Grace monitor started")
    while not _stop.is_set():
        try:
            await _grace_once()
        except Exception:  # noqa: BLE001
            logger.exception("Grace monitor error")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=5.0)
        except TimeoutError:
            pass
    logger.info("Grace monitor stopped")


async def escalation_loop() -> None:
    logger.info("Escalation monitor started")
    while not _stop.is_set():
        try:
            from app.services.escalation import run_escalations_once

            stats = await run_escalations_once()
            if stats["queued_escalated"] or stats["processing_escalated"]:
                logger.info("Escalations: %s", stats)
        except Exception:  # noqa: BLE001
            logger.exception("Escalation monitor error")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=60.0)
        except TimeoutError:
            pass
    logger.info("Escalation monitor stopped")


def start_dispatcher() -> None:
    global _dispatch_task, _grace_task, _escalation_task
    _stop.clear()
    if _dispatch_task and not _dispatch_task.done():
        return
    _dispatch_task = asyncio.create_task(dispatch_loop(), name="queue-dispatcher")
    _grace_task = asyncio.create_task(grace_loop(), name="grace-monitor")
    _escalation_task = asyncio.create_task(escalation_loop(), name="escalation-monitor")


async def stop_dispatcher() -> None:
    _stop.set()
    for t in (_dispatch_task, _grace_task, _escalation_task):
        if t:
            try:
                await asyncio.wait_for(t, timeout=5)
            except (TimeoutError, asyncio.CancelledError):
                t.cancel()
