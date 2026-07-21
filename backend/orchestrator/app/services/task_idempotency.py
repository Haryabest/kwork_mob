"""Идемпотентность задач §3.10 / §4.2 — already_processed + cached result URL."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Model3D, Order, TaskQueue
from app.services.minio import minio_service

logger = logging.getLogger(__name__)


def _parse_s3(url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    if url.startswith("s3://"):
        rest = url[5:]
        bucket, _, key = rest.partition("/")
        if bucket and key:
            return bucket, key
    if "/" in url and not url.startswith("http"):
        return settings.MINIO_BUCKET_MODELS, url.lstrip("/")
    return None


def presign_model_glb(model: Model3D, *, expires: int | None = None) -> str | None:
    from app.core.config import settings

    ttl = expires if expires is not None else int(settings.MODEL_PRESIGN_TTL_SECONDS or 1800)
    parsed = _parse_s3(model.glb_url)
    if not parsed:
        return model.glb_url if model.glb_url and model.glb_url.startswith("http") else None
    bucket, key = parsed
    try:
        return minio_service.generate_presigned_url(bucket, key, expires=ttl)
    except Exception as exc:  # noqa: BLE001
        logger.warning("presign glb %s: %s", model.uuid, exc)
        return None


async def completed_result(db: AsyncSession, task_id: str) -> dict[str, Any] | None:
    """Кэшированный результат для already_processed."""
    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    if not row or row.status != "done":
        return None
    order = await db.get(Order, row.order_id) if row.order_id else None
    model: Model3D | None = None
    if order:
        model = await db.scalar(select(Model3D).where(Model3D.order_id == order.id))
    if not model:
        model = await db.scalar(select(Model3D).where(Model3D.uuid == task_id))
    if not model or not model.glb_url:
        return None
    url = presign_model_glb(model)
    if not url:
        return None
    return {
        "status": "already_processed",
        "task_id": task_id,
        "result_url": url,
        "glb_url": url,
        "model_uuid": model.uuid,
        "order_id": order.id if order else None,
    }


async def skip_if_completed(db: AsyncSession, task_id: str) -> dict[str, Any] | None:
    """Перед dispatch: задача уже done → не отправлять воркеру."""
    cached = await completed_result(db, task_id)
    if not cached:
        return None
    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    if row and row.order_id:
        order = await db.get(Order, row.order_id)
        if order and order.status not in ("completed", "cancelled", "failed", "blocked_nsfw"):
            order.status = "completed"
            await db.flush()
    return cached
