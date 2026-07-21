"""Уведомления об истечении облачной копии исходников §3.4.3 / §9.1.2."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Model3D, Order, User
from app.services import company_notify as cn

logger = logging.getLogger(__name__)

# За 7, 3 и 1 день до удаления (§9.1.2)
WARN_DAYS = (7, 3, 1)


def ttl_days() -> int:
    return max(7, min(int(getattr(settings, "SOURCE_PHOTOS_TTL_DAYS", 30) or 30), 90))


def _aware(dt: datetime | None, now: datetime) -> datetime:
    if dt is None:
        return now
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _already_notified(redis, *, order_id: int, days_left: int) -> bool:
    key = f"source_expire:notified:{order_id}:{days_left}"
    return bool(await redis.get(key))


async def _mark_notified(redis, *, order_id: int, days_left: int) -> None:
    key = f"source_expire:notified:{order_id}:{days_left}"
    await redis.set(key, datetime.now(timezone.utc).isoformat(), ex=60 * 60 * 36)


async def notify_expiring_sources(db: AsyncSession, *, limit: int = 500) -> dict[str, Any]:
    """Celery daily: push/email «облачная копия истекает через N дней»."""
    now = datetime.now(timezone.utc)
    ttl = ttl_days()
    sent = 0
    skipped = 0
    scanned = 0
    by_days: dict[str, int] = {str(d): 0 for d in WARN_DAYS}

    try:
        from app.core.redis import get_redis

        redis = await get_redis()
    except Exception as exc:  # noqa: BLE001
        logger.warning("source_expire redis unavailable: %s", exc)
        return {"ok": False, "error": str(exc)[:200], "ttl_days": ttl}

    # Модели с заказами — исходники живут до source_expires_at (default TTL от created)
    rows = (
        await db.execute(
            select(Model3D, Order)
            .join(Order, Order.id == Model3D.order_id)
            .where(
                Order.status.in_(("completed", "paid", "processing", "queued")),
                Model3D.trashed_at.is_(None),
            )
            .order_by(Order.created_at.asc())
            .limit(limit)
        )
    ).all()

    from app.services import model_storage as ms

    for model, order in rows:
        scanned += 1
        exp = ms.ensure_expires(model)
        days_left = (exp.date() - now.date()).days
        if days_left not in WARN_DAYS:
            continue
        if await _already_notified(redis, order_id=order.id, days_left=days_left):
            skipped += 1
            continue

        title = "Облачная копия исходников истекает"
        label = (
            (model.display_name or "").strip()
            or (order.model_display_name or "").strip()
            or f"заказ #{order.id}"
        )
        body = (
            f"Облачная копия исходников «{label}» будет удалена через {days_left} "
            f"{'день' if days_left == 1 else 'дня' if days_left < 5 else 'дней'}. "
            f"Скачайте или продлите хранение (заказ #{order.id})."
        )
        data = {
            "order_id": str(order.id),
            "model_uuid": model.uuid,
            "days_left": str(days_left),
            "expire_at": exp.isoformat(),
            "event": "source_expire",
        }

        if order.company_id:
            result = await cn.notify_company_event(
                db,
                company_id=order.company_id,
                event="source_expire",
                title=title,
                body=body,
                data=data,
            )
            if result.get("sent", 0) > 0:
                sent += 1
                by_days[str(days_left)] += 1
                await _mark_notified(redis, order_id=order.id, days_left=days_left)
            else:
                skipped += 1
        else:
            user = await db.get(User, order.user_id)
            if not user:
                skipped += 1
                continue
            prefs = dict(user.notification_prefs or {})
            if prefs.get("source_expire") is False:
                skipped += 1
                continue
            if prefs.get("push_enabled") is False and prefs.get("email_enabled") is False:
                skipped += 1
                continue
            from app.services import push as push_svc

            r = await push_svc.send_to_user(
                db,
                user.id,
                title,
                body,
                data=data,
                email_fallback=True,
            )
            if r.get("delivered_push") or r.get("email_fallback"):
                sent += 1
                by_days[str(days_left)] += 1
                await _mark_notified(redis, order_id=order.id, days_left=days_left)
            else:
                skipped += 1

    await db.commit()
    return {
        "ok": True,
        "ttl_days": ttl,
        "warn_days": list(WARN_DAYS),
        "scanned": scanned,
        "sent": sent,
        "skipped": skipped,
        "by_days": by_days,
        "as_of": now.isoformat(),
    }
