"""Rate limiting: Redis sliding window + API-key limits (§10.4)."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """100 req/min на JWT user, 1000/min на IP; API-ключ — свой лимит из Redis."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/health") or request.method == "OPTIONS":
            return await call_next(request)

        try:
            from app.core.redis import get_redis

            redis = await get_redis()
        except Exception:  # noqa: BLE001
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        auth = request.headers.get("Authorization") or ""
        now = int(time.time())
        window = 60

        if api_key:
            prefix = api_key[:12]
            limit = int(getattr(settings, "API_KEY_DEFAULT_RATE_LIMIT", 1000) or 1000)
            try:
                cached = await redis.get(f"rl:apikey:cfg:{prefix}")
                if cached:
                    limit = int(cached)
            except Exception:  # noqa: BLE001
                pass
            # суточный лимит §12.4.1
            try:
                from app.services import api_key_limits as akl

                daily = await akl.check_and_incr_daily(prefix)
                if daily.get("exceeded"):
                    return JSONResponse(
                        {"detail": "Daily API key limit exceeded"},
                        status_code=429,
                        headers={"Retry-After": "3600"},
                    )
            except Exception:  # noqa: BLE001
                pass
            bucket = f"rl:apikey:{prefix}:{now // window}"
        elif auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1][:24]
            limit = 100
            bucket = f"rl:user:{token}:{now // window}"
        else:
            ip = request.client.host if request.client else "unknown"
            limit = 1000
            bucket = f"rl:ip:{ip}:{now // window}"

        try:
            count = await redis.incr(bucket)
            if count == 1:
                await redis.expire(bucket, window + 5)
            if count > limit:
                return JSONResponse(
                    {"detail": "Too Many Requests"},
                    status_code=429,
                    headers={"Retry-After": str(window)},
                )
        except Exception:  # noqa: BLE001
            pass

        return await call_next(request)


class RobotsTagMiddleware(BaseHTTPMiddleware):
    """X-Robots-Tag: noindex для всех страниц."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
        return response
