"""Напоминания о публикации 3 и 14 дней (§7.5.3)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Model3D, ModelPublicationLink, Order, User
from app.services import company_notify as cn

logger = logging.getLogger(__name__)

REMINDER_DAYS = (3, 14)
PUBLISHED_MARKERS = ("published", "verified", "api_uploaded")


def needs_publish_reminder(publish_status: str | None) -> bool:
    ps = (publish_status or "not_published").lower().strip()
    if ps in ("", "none", "not_published"):
        return True
    return not any(m in ps for m in PUBLISHED_MARKERS)


def reminder_copy(days: int) -> tuple[str, str]:
    if days == 3:
        return (
            "Опубликуйте 3D-модель",
            "Не забудьте опубликовать 3D-модель на маркетплейсе, чтобы повысить конверсию. "
            "Добавьте ссылку на карточку товара и получите бонус!",
        )
    return (
        "Помощь с публикацией 3D",
        "Прошло 2 недели с момента генерации модели. Нужна помощь с публикацией на WB/Ozon? "
        "Откройте инструкцию в приложении или напишите в поддержку.",
    )


async def _already_notified(redis, *, model_uuid: str, days: int) -> bool:
    key = f"publish_reminder:notified:{model_uuid}:{days}"
    return bool(await redis.get(key))


async def _mark_notified(redis, *, model_uuid: str, days: int) -> None:
    key = f"publish_reminder:notified:{model_uuid}:{days}"
    await redis.set(key, datetime.now(timezone.utc).isoformat(), ex=60 * 60 * 24 * 45)


async def _has_verified_link(db: AsyncSession, model_uuid: str) -> bool:
    n = await db.scalar(
        select(func.count())
        .select_from(ModelPublicationLink)
        .where(
            ModelPublicationLink.model_uuid == model_uuid,
            ModelPublicationLink.status == "verified",
        )
    )
    return int(n or 0) > 0


async def notify_publish_reminders(db: AsyncSession, *, limit: int = 500) -> dict[str, Any]:
    """Celery daily: push/email если модель не опубликована через 3/14 дней."""
    now = datetime.now(timezone.utc)
    sent = 0
    skipped = 0
    scanned = 0
    by_days: dict[str, int] = {str(d): 0 for d in REMINDER_DAYS}

    try:
        from app.core.redis import get_redis

        redis = await get_redis()
    except Exception as exc:  # noqa: BLE001
        logger.warning("publish_reminder redis unavailable: %s", exc)
        return {"ok": False, "error": str(exc)[:200]}

    rows = (
        await db.execute(
            select(Model3D, Order)
            .join(Order, Order.id == Model3D.order_id)
            .where(
                Model3D.trashed_at.is_(None),
                Model3D.glb_url.isnot(None),
                Order.status.in_(("completed", "paid", "processing", "queued")),
            )
            .order_by(Model3D.created_at.asc())
            .limit(limit)
        )
    ).all()

    for model, order in rows:
        scanned += 1
        if not needs_publish_reminder(model.publish_status):
            skipped += 1
            continue
        if await _has_verified_link(db, model.uuid):
            skipped += 1
            continue

        created = model.created_at
        if created is None:
            skipped += 1
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        days_since = (now.date() - created.date()).days
        if days_since not in REMINDER_DAYS:
            continue
        if await _already_notified(redis, model_uuid=model.uuid, days=days_since):
            skipped += 1
            continue

        title, body = reminder_copy(days_since)
        data = {
            "model_uuid": model.uuid,
            "order_id": str(order.id),
            "days_since_generation": str(days_since),
            "event": "publish_reminder",
        }

        if model.company_id:
            result = await cn.notify_company_event(
                db,
                company_id=model.company_id,
                event="publish_reminder",
                title=title,
                body=body,
                data=data,
            )
            if result.get("sent", 0) > 0:
                sent += 1
                by_days[str(days_since)] += 1
                await _mark_notified(redis, model_uuid=model.uuid, days=days_since)
            else:
                skipped += 1
        else:
            user = await db.get(User, order.user_id)
            if not user:
                skipped += 1
                continue
            prefs = dict(user.notification_prefs or {})
            if prefs.get("publish_reminder") is False:
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
                by_days[str(days_since)] += 1
                await _mark_notified(redis, model_uuid=model.uuid, days=days_since)
            else:
                skipped += 1

    await db.commit()
    return {
        "ok": True,
        "reminder_days": list(REMINDER_DAYS),
        "scanned": scanned,
        "sent": sent,
        "skipped": skipped,
        "by_days": by_days,
        "as_of": now.isoformat(),
    }
