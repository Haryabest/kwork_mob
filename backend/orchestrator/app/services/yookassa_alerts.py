"""Счётчик подряд идущих ошибок ЮKassa → Telegram + email (§12.4.1)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import get_redis
from app.services import alerts as alerts_svc

logger = logging.getLogger(__name__)

REDIS_KEY = "yookassa:error_streak"
EVENT = "yookassa_errors"


def _threshold() -> int:
    return int(getattr(settings, "YOOKASSA_ERROR_STREAK_ALERT", 5) or 5)


async def record_success() -> None:
    try:
        redis = await get_redis()
        await redis.delete(REDIS_KEY)
    except Exception as exc:  # noqa: BLE001
        logger.warning("yookassa streak reset failed: %s", exc)


async def record_error(detail: str = "") -> dict[str, Any]:
    """Инкремент streak; при >N — dual alert."""
    streak = 0
    try:
        redis = await get_redis()
        streak = int(await redis.incr(REDIS_KEY))
        await redis.expire(REDIS_KEY, 86400)
    except Exception as exc:  # noqa: BLE001
        logger.warning("yookassa streak incr failed: %s", exc)
        return {"streak": 0, "alerted": False}

    thr = _threshold()
    alerted = False
    if streak >= thr:
        text = (
            f"🚨 Ошибки ЮKassa >{thr} подряд\n"
            f"streak: {streak}\n"
            f"detail: {(detail or '')[:400]}"
        )
        try:
            async with async_session() as db:
                dual = await alerts_svc.send_dual(
                    db,
                    text,
                    event_type=EVENT,
                    payload={"fingerprint": f"yk_streak:{streak // thr}", "streak": streak},
                    subject=f"[3dvektor] YooKassa errors streak={streak}",
                )
                await db.commit()
                alerted = bool(dual.get("telegram") or dual.get("email"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("yookassa alert failed: %s", exc)
    return {"streak": streak, "alerted": alerted, "threshold": thr}


async def current_streak() -> int:
    try:
        redis = await get_redis()
        return int(await redis.get(REDIS_KEY) or 0)
    except Exception:  # noqa: BLE001
        return 0
