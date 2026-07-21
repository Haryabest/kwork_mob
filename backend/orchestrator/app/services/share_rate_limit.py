"""Rate limit публичного share viewer (§3.12)."""

from __future__ import annotations

import time

from fastapi import HTTPException, Request

from app.core.config import settings

WINDOW_SEC = 60
DEFAULT_LIMIT = settings.SHARE_VIEW_RATE_LIMIT or 30


async def assert_share_allowed(request: Request, short_hash: str) -> None:
    from app.core.redis import get_redis

    ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    now = int(time.time())
    bucket = f"rl:share:{short_hash}:{ip}:{now // WINDOW_SEC}"
    try:
        redis = await get_redis()
        count = await redis.incr(bucket)
        if count == 1:
            await redis.expire(bucket, WINDOW_SEC + 5)
        if count > DEFAULT_LIMIT:
            raise HTTPException(429, "Слишком много запросов к просмотрщику", headers={"Retry-After": str(WINDOW_SEC)})
    except HTTPException:
        raise
    except Exception:
        return
