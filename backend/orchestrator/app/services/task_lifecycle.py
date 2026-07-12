"""Жизненный цикл задачи: статусы заказа, Model3D, события WS."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import get_redis
from app.models import Model3D, Order, TaskQueue, WorkerNode
from app.services.events import publish_order_status
from app.services.queue import queue_service

logger = logging.getLogger(__name__)


async def upsert_worker_heartbeat(
    db: AsyncSession,
    worker_id: str,
    *,
    status: str,
    gpu_name: str | None = None,
    gpu_load: float | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    from datetime import datetime, timezone

    node = await db.get(WorkerNode, worker_id)
    if not node:
        node = WorkerNode(id=worker_id)
        db.add(node)
    node.status = status
    if gpu_name is not None:
        node.gpu_name = gpu_name
    if gpu_load is not None:
        node.gpu_load = gpu_load
    node.last_heartbeat = datetime.now(timezone.utc)
    if meta:
        node.meta = {**(node.meta or {}), **meta}
    await db.commit()


async def mark_processing(db: AsyncSession, task_id: str, worker_id: str) -> Order | None:
    from datetime import datetime, timezone

    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    order = None
    if row:
        row.status = "processing"
        row.worker_id = worker_id
        row.processing_started_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        order = await db.get(Order, row.order_id)
        if order and order.status in ("queued", "paid"):
            order.status = "processing"
        await db.commit()
        if order:
            await publish_order_status(
                user_id=order.user_id,
                order_id=order.id,
                task_id=task_id,
                status="processing",
                extra={"worker_id": worker_id},
            )
    return order


async def mark_completed(
    db: AsyncSession,
    *,
    task_id: str,
    glb_url: str,
    usdz_url: str | None = None,
    watermark_hmac: str | None = None,
) -> Order | None:
    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    if not row:
        return None
    row.status = "done"
    order = await db.get(Order, row.order_id)
    if not order:
        await db.commit()
        return None

    order.status = "completed"
    existing = await db.scalar(select(Model3D).where(Model3D.order_id == order.id))
    if existing:
        existing.glb_url = glb_url
        if usdz_url:
            existing.usdz_url = usdz_url
        if watermark_hmac:
            existing.watermark_hmac = watermark_hmac
    else:
        db.add(
            Model3D(
                uuid=str(uuid.uuid4()),
                order_id=order.id,
                user_id=order.user_id,
                company_id=order.company_id,
                glb_url=glb_url,
                usdz_url=usdz_url,
                watermark_hmac=watermark_hmac,
                publish_status="not_published",
            )
        )
    await db.flush()
    try:
        from app.services import company_webhooks as wh

        await wh.emit(
            db,
            company_id=order.company_id,
            event="model.generated",
            payload={
                "order_id": order.id,
                "task_id": task_id,
                "glb_url": glb_url,
                "usdz_url": usdz_url,
            },
        )
        await wh.emit(
            db,
            company_id=order.company_id,
            event="order.completed",
            payload={"order_id": order.id, "task_id": task_id},
        )
    except Exception:  # noqa: BLE001
        pass
    await db.commit()
    await publish_order_status(
        user_id=order.user_id,
        order_id=order.id,
        task_id=task_id,
        status="completed",
        extra={"glb_url": glb_url},
    )
    return order


async def mark_failed(db: AsyncSession, task_id: str, error: str) -> Order | None:
    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    if not row:
        return None
    row.status = "failed"
    order = await db.get(Order, row.order_id)
    if order and order.status not in ("cancelled", "completed"):
        order.status = "failed"
    await db.commit()
    if order:
        await publish_order_status(
            user_id=order.user_id,
            order_id=order.id,
            task_id=task_id,
            status="failed",
            extra={"error": error[:500]},
        )
    return order


async def requeue_task(task_id: str) -> None:
    """Вернуть задачу в Redis при обрыве воркера."""
    import json

    async with async_session() as db:
        row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
        if not row or row.status not in ("processing", "queued"):
            return
        order = await db.get(Order, row.order_id)
        if order and order.status in ("processing", "queued"):
            order.status = "queued"
        row.status = "queued"
        row.processing_started_at = None
        row.worker_id = None
        payload = row.payload_json or {}
        await db.commit()
        redis = await get_redis()
        key = queue_service._key(row.priority)
        await redis.lpush(
            key,
            json.dumps(
                {"task_id": row.task_id, "order_id": row.order_id, "payload": payload},
                ensure_ascii=False,
            ),
        )
        if order:
            await publish_order_status(
                user_id=order.user_id,
                order_id=order.id,
                task_id=task_id,
                status="queued",
                extra={"requeued": True},
            )


async def try_queue_awaiting_orders(db: AsyncSession, user_id: int) -> list[int]:
    """После пополнения баланса — поставить awaiting_payment в очередь."""
    from app.models import Transaction, User

    user = await db.get(User, user_id)
    if not user:
        return []
    orders = (
        await db.scalars(
            select(Order).where(Order.user_id == user_id, Order.status == "awaiting_payment").order_by(Order.id)
        )
    ).all()
    queued_ids: list[int] = []
    from app.services.nsfw import nsfw_service

    for order in orders:
        if user.balance < order.amount:
            break
        nsfw = await nsfw_service.check_task_photos(order.task_uuid)
        if nsfw.get("is_nsfw"):
            await nsfw_service.block_order(
                db, order=order, user=user, result=nsfw, refund=True, charged=False
            )
            continue
        user.balance -= order.amount
        db.add(
            Transaction(
                user_id=user.id,
                company_id=order.company_id,
                amount=-order.amount,
                tx_type="charge",
                description=f"Заказ #{order.id} (после оплаты)",
            )
        )
        order.status = "queued"
        payload = {
            "category": order.category,
            "tier": order.tier,
            "user_id": user.id,
            "photos_bucket": settings.MINIO_BUCKET_PHOTOS,
            "photos_prefix": f"photos/{order.task_uuid}/",
            "models_bucket": settings.MINIO_BUCKET_MODELS,
        }
        await queue_service.enqueue(
            db,
            task_id=order.task_uuid,
            order_id=order.id,
            company_id=order.company_id,
            payload=payload,
            priority="high" if order.tier == "large" else "normal",
        )
        queued_ids.append(order.id)
        await publish_order_status(
            user_id=user.id,
            order_id=order.id,
            task_id=order.task_uuid,
            status="queued",
        )
    await db.commit()
    return queued_ids
