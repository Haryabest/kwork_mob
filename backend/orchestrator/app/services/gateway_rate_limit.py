"""API Gateway rate limits §4.1.3 / §10.4."""

from __future__ import annotations

import time
from typing import Any

from starlette.requests import Request

from app.core.config import settings


def client_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("X-Real-IP") or request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else "unknown"


async def load_limits() -> dict[str, int]:
    defaults = {
        "gateway_ip_rate_limit_per_min": int(getattr(settings, "GATEWAY_IP_RATE_LIMIT_PER_MIN", 1000) or 1000),
        "gateway_jwt_rate_limit_per_min": int(getattr(settings, "GATEWAY_JWT_RATE_LIMIT_PER_MIN", 100) or 100),
        "gateway_rate_block_sec": int(getattr(settings, "GATEWAY_RATE_BLOCK_SEC", 300) or 300),
    }
    try:
        from app.services.alert_thresholds import threshold_async

        for key in defaults:
            defaults[key] = int(await threshold_async(key, defaults[key]))
    except Exception:  # noqa: BLE001
        pass
    return defaults


def bearer_user_id(auth: str) -> str | None:
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        from app.core.security import TokenType, decode_token

        payload = decode_token(token, TokenType.ACCESS)
        sub = payload.get("sub")
        return str(sub) if sub is not None else None
    except Exception:  # noqa: BLE001
        return None


async def check_request(request: Request, redis: Any) -> tuple[bool, int, str]:
    """Returns (allowed, retry_after_sec, detail)."""
    limits = await load_limits()
    window = 60
    block_sec = limits["gateway_rate_block_sec"]
    now = int(time.time())

    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    auth = request.headers.get("Authorization") or ""

    if api_key:
        prefix = api_key[:12]
        limit = int(getattr(settings, "API_KEY_DEFAULT_RATE_LIMIT", 1000) or 1000)
        try:
            cached = await redis.get(f"rl:apikey:cfg:{prefix}")
            if cached:
                limit = int(cached)
        except Exception:  # noqa: BLE001
            pass
        block_key = f"rl:block:apikey:{prefix}"
        bucket = f"rl:apikey:{prefix}:{now // window}"
        kind = "apikey"
    elif auth.lower().startswith("bearer "):
        uid = bearer_user_id(auth) or auth.split(" ", 1)[1][:24]
        limit = limits["gateway_jwt_rate_limit_per_min"]
        block_key = f"rl:block:user:{uid}"
        bucket = f"rl:user:{uid}:{now // window}"
        kind = "jwt"
    else:
        ip = client_ip(request)
        limit = limits["gateway_ip_rate_limit_per_min"]
        block_key = f"rl:block:ip:{ip}"
        bucket = f"rl:ip:{ip}:{now // window}"
        kind = "ip"

    try:
        if await redis.get(block_key):
            return False, block_sec, f"Blocked ({kind})"
        count = await redis.incr(bucket)
        if count == 1:
            await redis.expire(bucket, window + 5)
        if count > limit:
            await redis.setex(block_key, block_sec, "1")
            return False, block_sec, "Too Many Requests"
    except Exception:  # noqa: BLE001
        return True, 0, ""
    return True, 0, ""
