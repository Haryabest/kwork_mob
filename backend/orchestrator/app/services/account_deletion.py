"""Право на забвение §2.8.3 / §11.12: удаление ПДн, финансы анонимизируются на 5 лет."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    DeletionRequest,
    DeviceToken,
    Model3D,
    Order,
    RefreshToken,
    Transaction,
    User,
)
from app.services.minio import minio_service

logger = logging.getLogger(__name__)

DELETION_SLA_DAYS = 30
FINANCE_RETENTION_YEARS = 5


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


async def request_deletion(db: AsyncSession, user: User) -> DeletionRequest:
    if user.status == "deleted":
        raise HTTPException(400, "Аккаунт уже удалён")
    existing = await db.scalar(
        select(DeletionRequest).where(
            DeletionRequest.user_id == user.id,
            DeletionRequest.status.in_(("pending", "processing")),
        )
    )
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    row = DeletionRequest(
        user_id=user.id,
        email_hash=_email_hash(user.email),
        status="pending",
        requested_at=now,
        due_at=now + timedelta(days=DELETION_SLA_DAYS),
        meta={"email_domain": user.email.split("@")[-1] if "@" in user.email else None},
    )
    db.add(row)
    user.status = "deletion_pending"
    await db.flush()
    return row


async def _purge_minio_for_user(db: AsyncSession, user_id: int) -> int:
    deleted = 0
    models = (await db.scalars(select(Model3D).where(Model3D.user_id == user_id))).all()
    orders = (await db.scalars(select(Order).where(Order.user_id == user_id))).all()
    for m in models:
        for url in (m.glb_url, m.usdz_url):
            if not url:
                continue
            key = None
            bucket = settings.MINIO_BUCKET_MODELS
            if url.startswith("s3://"):
                rest = url[5:]
                bucket, _, key = rest.partition("/")
            elif "/" in url and not url.startswith("http"):
                key = url.lstrip("/")
            if key:
                try:
                    minio_service.client.delete_object(Bucket=bucket, Key=key)
                    deleted += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("MinIO delete %s: %s", key, exc)
    for o in orders:
        prefix = f"photos/{o.task_uuid}/"
        for i in range(12):
            key = f"{prefix}view_{i:02d}.jpg"
            try:
                if minio_service.object_exists(settings.MINIO_BUCKET_PHOTOS, key):
                    minio_service.client.delete_object(Bucket=settings.MINIO_BUCKET_PHOTOS, Key=key)
                    deleted += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("MinIO photo delete %s: %s", key, exc)
        for extra in ("source.zip", "metadata.json"):
            key = f"{prefix}{extra}"
            try:
                if minio_service.object_exists(settings.MINIO_BUCKET_PHOTOS, key):
                    minio_service.client.delete_object(Bucket=settings.MINIO_BUCKET_PHOTOS, Key=key)
                    deleted += 1
            except Exception:  # noqa: BLE001
                pass
    return deleted


async def execute_deletion(
    db: AsyncSession,
    *,
    user_id: int,
    processed_by: int | None = None,
) -> dict:
    """Физическое удаление ПДн; Transaction — анонимизация (user_id=NULL) на 5 лет."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    req = await db.scalar(
        select(DeletionRequest).where(
            DeletionRequest.user_id == user_id,
            DeletionRequest.status.in_(("pending", "processing")),
        )
    )
    if req:
        req.status = "processing"

    objects_deleted = await _purge_minio_for_user(db, user_id)

    # отзыв сессий и device tokens
    tokens = (await db.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id))).all()
    for t in tokens:
        t.revoked = True
    devices = (await db.scalars(select(DeviceToken).where(DeviceToken.user_id == user_id))).all()
    for d in devices:
        await db.delete(d)

    now = datetime.now(timezone.utc)
    txs = (await db.scalars(select(Transaction).where(Transaction.user_id == user_id))).all()
    for tx in txs:
        tx.user_id = None
        tx.anonymized_at = now
        tx.description = f"[anonymized] finance retention {FINANCE_RETENTION_YEARS}y"

    models = (await db.scalars(select(Model3D).where(Model3D.user_id == user_id))).all()
    for m in models:
        m.glb_url = None
        m.usdz_url = None

    email_was = user.email
    user.email = f"deleted_{user.id}@removed.local"
    user.full_name = None
    user.phone = None
    user.password_hash = "!"
    user.totp_secret = None
    user.totp_enabled = False
    user.balance = 0
    user.status = "deleted"
    user.marketing_opt_in = False

    if req:
        req.status = "done"
        req.processed_at = now
        req.processed_by = processed_by
        req.user_id = None
        req.meta = {**(req.meta or {}), "objects_deleted": objects_deleted, "email_was_hash": _email_hash(email_was)}

    await db.flush()
    return {
        "user_id": user_id,
        "status": "deleted",
        "objects_deleted": objects_deleted,
        "finance_retained_years": FINANCE_RETENTION_YEARS,
    }


async def process_due_deletions(db: AsyncSession) -> int:
    """Celery: исполнить запросы старше 30 дней."""
    now = datetime.now(timezone.utc)
    rows = (
        await db.scalars(
            select(DeletionRequest).where(
                DeletionRequest.status == "pending",
                DeletionRequest.due_at <= now,
            )
        )
    ).all()
    n = 0
    for row in rows:
        if row.user_id:
            await execute_deletion(db, user_id=row.user_id)
            n += 1
    await db.commit()
    return n
