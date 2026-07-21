"""reCAPTCHA v3 для регистрации и оплаты — подозрительные аккаунты (§10.10)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User
from app.services.login_guard import verify_recaptcha

# Базовый список disposable-доменов (расширяется через env)
_DISPOSABLE_DOMAINS = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "guerrillamail.net",
        "tempmail.com",
        "10minutemail.com",
        "yopmail.com",
        "throwaway.email",
        "sharklasers.com",
        "trashmail.com",
        "getnada.com",
    }
)


def _extra_disposable_domains() -> frozenset[str]:
    raw = (settings.CAPTCHA_DISPOSABLE_DOMAINS or "").strip()
    if not raw:
        return frozenset()
    return frozenset(d.strip().lower() for d in raw.split(",") if d.strip())


def is_disposable_email(email: str) -> bool:
    domain = email.split("@")[-1].lower()
    return domain in _DISPOSABLE_DOMAINS or domain in _extra_disposable_domains()


def is_suspicious_register_email(email: str) -> bool:
    if settings.RECAPTCHA_ENFORCE_REGISTER:
        return True
    return is_disposable_email(email)


async def is_suspicious_payment_user(db: AsyncSession, user: User) -> bool:
    if settings.RECAPTCHA_ENFORCE_PAYMENT:
        return True
    if is_disposable_email(user.email):
        return True
    created = user.created_at
    if created:
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created < timedelta(hours=24):
            return True
    return False


async def require_register_captcha(ip: str, email: str, captcha_token: str | None) -> None:
    if not is_suspicious_register_email(email):
        return
    if not captcha_token:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Требуется проверка captcha",
                "requires_captcha": True,
                "reason": "suspicious_register",
            },
        )
    await verify_recaptcha(captcha_token, ip)


async def require_payment_captcha(
    db: AsyncSession,
    user: User,
    ip: str,
    captcha_token: str | None,
) -> None:
    if not await is_suspicious_payment_user(db, user):
        return
    if not captcha_token:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Требуется проверка captcha перед оплатой",
                "requires_captcha": True,
                "reason": "suspicious_payment",
            },
        )
    await verify_recaptcha(captcha_token, ip)
