"""Суточный лимит API-ключа → Email владельцу сервиса (§12.4.1)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import get_redis
from app.services import alerts as alerts_svc

logger = logging.getLogger(__name__)

EVENT = "api_key_daily_limit"


def default_daily_limit() -> int:
    try:
        from app.services.alert_thresholds import threshold_sync

        return int(threshold_sync("api_key_default_daily_limit", 100_000))
    except Exception:  # noqa: BLE001
        return int(getattr(settings, "API_KEY_DEFAULT_DAILY_LIMIT", 100_000) or 100_000)


async def check_and_incr_daily(prefix: str, *, company_id: int | None = None) -> dict[str, Any]:
    """
    Инкремент суточного счётчика. exceeded=True если лимит исчерпан.
    При первом превышении — email alert.
    """
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    limit = default_daily_limit()
    try:
        redis = await get_redis()
        cached = await redis.get(f"rl:apikey:daily_cfg:{prefix}")
        if cached:
            limit = int(cached)
        key = f"rl:apikey:day:{prefix}:{day}"
        count = int(await redis.incr(key))
        if count == 1:
            await redis.expire(key, 86400 + 3600)
    except Exception as exc:  # noqa: BLE001
        logger.warning("api key daily incr: %s", exc)
        return {"count": 0, "limit": limit, "exceeded": False}

    exceeded = count > limit
    if exceeded and count == limit + 1:
        text = (
            f"📧 Превышен суточный лимит API-ключа\n"
            f"key_prefix: {prefix}\n"
            f"company_id: {company_id or '—'}\n"
            f"count: {count}\n"
            f"limit: {limit}"
        )
        try:
            async with async_session() as db:
                await alerts_svc.send_dual(
                    db,
                    text,
                    event_type=EVENT,
                    payload={
                        "fingerprint": f"api_day:{prefix}:{day}",
                        "key_prefix": prefix,
                        "company_id": company_id,
                        "count": count,
                        "limit": limit,
                    },
                    subject=f"[3dvektor] API key daily limit {prefix}",
                    telegram=False,
                    email=True,
                )
                await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("api key daily alert: %s", exc)
    return {"count": count, "limit": limit, "exceeded": exceeded}
