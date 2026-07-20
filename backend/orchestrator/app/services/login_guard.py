"""Защита login: счётчик неудач + reCAPTCHA v3 (§20.10.2 / §10)."""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

LOGIN_FAIL_PREFIX = "login_fail:"
LOGIN_BLOCK_PREFIX = "login_block:"
LOGIN_FAIL_MAX = 5
LOGIN_BLOCK_SECONDS = 300
LOGIN_FAIL_TTL = 3600


def _keys(ip: str, email: str) -> tuple[str, str]:
    norm = email.lower().strip()
    return f"{LOGIN_FAIL_PREFIX}{ip}:{norm}", f"{LOGIN_BLOCK_PREFIX}{ip}:{norm}"


async def assert_login_allowed(ip: str, email: str) -> None:
    redis = await get_redis()
    _, block_key = _keys(ip, email)
    if await redis.get(block_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Слишком много попыток. Попробуйте через 5 минут",
                "requires_captcha": True,
                "blocked": True,
            },
        )


async def login_status(ip: str, email: str) -> dict:
    redis = await get_redis()
    fail_key, block_key = _keys(ip, email)
    blocked = bool(await redis.get(block_key))
    failures = int(await redis.get(fail_key) or 0)
    return {
        "requires_captcha": blocked or failures >= LOGIN_FAIL_MAX,
        "failures": failures,
        "blocked": blocked,
    }


async def require_captcha_if_needed(ip: str, email: str, captcha_token: str | None) -> None:
    st = await login_status(ip, email)
    if not st["requires_captcha"]:
        return
    if not captcha_token:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Требуется проверка captcha",
                "requires_captcha": True,
                "blocked": st["blocked"],
            },
        )
    await verify_recaptcha(captcha_token, ip)


async def verify_recaptcha(token: str, remote_ip: str | None) -> None:
    secret = settings.RECAPTCHA_SECRET_KEY.strip()
    if not secret:
        if settings.is_development:
            return
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Captcha не настроена на сервере")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": secret,
                    "response": token,
                    "remoteip": remote_ip or "",
                },
            )
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("recaptcha verify failed: %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Captcha недоступна") from exc
    if not data.get("success"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Captcha не пройдена")
    score = float(data.get("score", 1.0))
    if score < settings.RECAPTCHA_MIN_SCORE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Captcha не пройдена")


async def record_login_failure(ip: str, email: str) -> dict:
    redis = await get_redis()
    fail_key, block_key = _keys(ip, email)
    n = await redis.incr(fail_key)
    if n == 1:
        await redis.expire(fail_key, LOGIN_FAIL_TTL)
    if n >= LOGIN_FAIL_MAX:
        await redis.set(block_key, "1", ex=LOGIN_BLOCK_SECONDS)
    return await login_status(ip, email)


async def clear_login_failures(ip: str, email: str) -> None:
    redis = await get_redis()
    fail_key, block_key = _keys(ip, email)
    await redis.delete(fail_key, block_key)
