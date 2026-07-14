"""Shoot-link: expire + photo TTL 7d cleanup (§3.15.4)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Order, ShootLink
from app.services import photos as photos_svc
from app.services.shoot_links import expire_stale

logger = logging.getLogger(__name__)

# статусы, при которых генерация уже запущена / завершена — фото не трогаем
_GEN_STARTED = frozenset(
    {
        "paid",
        "queued",
        "processing",
        "completed",
        "done",
        "blocked_nsfw",
        "nsfw_blocked",
    }
)


def _photo_ttl_days() -> int:
    return int(getattr(settings, "SHOOT_LINK_PHOTO_TTL_DAYS", 7) or 7)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _mark_uploaded(link: ShootLink) -> None:
    meta = dict(link.meta or {})
    if not meta.get("photos_uploaded_at"):
        meta["photos_uploaded_at"] = datetime.now(timezone.utc).isoformat()
        link.meta = meta


async def cleanup_stale_photos(db: AsyncSession, *, limit: int = 500) -> dict[str, Any]:
    """
    Удалить photos/{task_uuid}/ через 7 дней, если генерация не запущена (§3.15.4).
    """
    expired_n = await expire_stale(db)
    ttl = timedelta(days=_photo_ttl_days())
    cutoff = datetime.now(timezone.utc) - ttl

    rows = (
        await db.scalars(
            select(ShootLink)
            .where(
                or_(
                    ShootLink.used_count > 0,
                    ShootLink.status.in_(("used", "expired", "revoked")),
                )
            )
            .order_by(ShootLink.id.asc())
            .limit(limit)
        )
    ).all()

    cleaned: list[dict[str, Any]] = []
    skipped = 0
    for link in rows:
        meta = dict(link.meta or {})
        if meta.get("photos_cleaned_at"):
            skipped += 1
            continue
        uploaded_raw = meta.get("photos_uploaded_at")
        try:
            uploaded_at = (
                datetime.fromisoformat(str(uploaded_raw).replace("Z", "+00:00"))
                if uploaded_raw
                else _aware(link.created_at)
            )
        except Exception:  # noqa: BLE001
            uploaded_at = _aware(link.created_at)
        if uploaded_at is None or uploaded_at > cutoff:
            continue

        order = await db.scalar(select(Order).where(Order.task_uuid == link.task_uuid))
        if order and order.status in _GEN_STARTED:
            skipped += 1
            continue

        try:
            result = photos_svc.delete_task_photos(link.task_uuid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("shoot photo cleanup %s: %s", link.task_uuid, exc)
            continue
        meta["photos_cleaned_at"] = datetime.now(timezone.utc).isoformat()
        meta["photos_cleaned_deleted"] = result.get("deleted", 0)
        link.meta = meta
        cleaned.append(
            {
                "shoot_link_id": link.id,
                "task_uuid": link.task_uuid,
                "deleted": result.get("deleted", 0),
            }
        )

    await db.commit()
    return {
        "ok": True,
        "ttl_days": _photo_ttl_days(),
        "expired_links": expired_n,
        "cleaned": len(cleaned),
        "skipped": skipped,
        "items": cleaned[:50],
    }
