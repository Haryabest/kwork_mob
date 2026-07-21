"""Rate limiting: Redis sliding window + API-key limits (§10.4)."""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.services import gateway_rate_limit as gw_rl


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Gateway: 1000/min IP, 100/min JWT user, API-key — свой лимит; block 5 мин (§4.1.3)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/health") or request.method == "OPTIONS":
            return await call_next(request)
        if os.getenv("RATE_LIMIT_DISABLED", "").lower() in ("1", "true", "yes"):
            return await call_next(request)

        try:
            from app.core.redis import get_redis

            redis = await get_redis()
        except Exception:  # noqa: BLE001
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if api_key:
            try:
                from app.services import api_key_limits as akl

                prefix = api_key[:12]
                daily = await akl.check_and_incr_daily(prefix)
                if daily.get("exceeded"):
                    return JSONResponse(
                        {"detail": "Daily API key limit exceeded"},
                        status_code=429,
                        headers={"Retry-After": "3600"},
                    )
            except Exception:  # noqa: BLE001
                pass

        allowed, retry_after, detail = await gw_rl.check_request(request, redis)
        if not allowed:
            return JSONResponse(
                {"detail": detail or "Too Many Requests"},
                status_code=429,
                headers={"Retry-After": str(retry_after or 60)},
            )

        return await call_next(request)


class RobotsTagMiddleware(BaseHTTPMiddleware):
    """X-Robots-Tag: noindex для всех страниц."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
        return response


class ApiRequestLogMiddleware(BaseHTTPMiddleware):
    """Пишет 4xx/5xx API в service_log_events для /admin/logs (§11.5)."""

    _SKIP_SUFFIXES = ("/admin/logs", "/health", "/metrics")

    async def dispatch(self, request: Request, call_next) -> Response:
        import time

        path = request.url.path
        if not path.startswith("/api/v1") or any(path.endswith(s) for s in self._SKIP_SUFFIXES):
            return await call_next(request)

        started = time.perf_counter()
        response = await call_next(request)
        status = response.status_code
        if status < 400:
            return response

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        level = "ERROR" if status >= 500 else "WARNING"
        message = f"{request.method} {path} {status} {elapsed_ms}ms"
        try:
            from app.core.database import async_session
            from app.services.log_writer import emit_log

            async with async_session() as db:
                await emit_log(
                    db,
                    source="api",
                    level=level,
                    message=message,
                    details={"status": status, "path": path, "method": request.method},
                )
                await db.commit()
        except Exception:  # noqa: BLE001
            pass
        return response
