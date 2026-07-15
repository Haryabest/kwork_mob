"""Отложенный email-fallback для push (§3.4.3).

Если push доставлен, но пользователь не открыл уведомление за 5 минут —
дублируем сообщение на email. Планирование в Redis (ZSET по времени),
без отдельной таблицы. Обрабатывается Celery-задачей раз в минуту.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserNotification

logger = logging.getLogger(__name__)

DUE_ZSET = "push:fallback:due"
ITEM_HASH = "push:fallback:item"
DEFAULT_DELAY_SEC = 300


async def schedule(
    redis,
    *,
    key: str,
    notif_id: int | None,
    user_id: int,
    email: str,
    title: str,
    body: str,
    delay: int = DEFAULT_DELAY_SEC,
) -> None:
    """Запланировать email-fallback через `delay` секунд."""
    payload = json.dumps(
        {
            "notif_id": notif_id,
            "user_id": user_id,
            "email": email,
            "title": title,
            "body": body,
        },
        ensure_ascii=False,
    )
    try:
        await redis.hset(ITEM_HASH, key, payload)
        await redis.zadd(DUE_ZSET, {key: time.time() + delay})
    except Exception as exc:  # noqa: BLE001
        logger.warning("push fallback schedule %s: %s", key, exc)


async def process_due(
    db: AsyncSession,
    redis,
    *,
    now: float | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Отправить email по просроченным записям, если уведомление не открыто."""
    now = now if now is not None else time.time()
    due = await redis.zrangebyscore(DUE_ZSET, 0, now, start=0, num=limit)
    sent = 0
    skipped = 0
    for raw_key in due:
        key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
        raw = await redis.hget(ITEM_HASH, key)
        await redis.zrem(DUE_ZSET, key)
        await redis.hdel(ITEM_HASH, key)
        if not raw:
            continue
        try:
            item = json.loads(raw)
        except (ValueError, TypeError):
            continue
        notif_id = item.get("notif_id")
        if notif_id:
            notif = await db.get(UserNotification, int(notif_id))
            # уведомление уже открыто в приложении — email не нужен
            if notif and notif.read_at is not None:
                skipped += 1
                continue
        email = item.get("email")
        if not email:
            skipped += 1
            continue
        try:
            from app.services import email as email_svc

            await email_svc.send_notification_email(
                email, item.get("title") or "Уведомление", item.get("body") or ""
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("push fallback email %s: %s", key, exc)
            skipped += 1
    return {"due": len(due), "sent": sent, "skipped": skipped}
