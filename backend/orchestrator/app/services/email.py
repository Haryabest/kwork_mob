"""Отправка email (SMTP или dev-режим)."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_verification_email(email: str, code: str) -> str | None:
    """Отправляет 6-значный код. В dev возвращает код для отладки."""
    subject = "KWork Mob — код подтверждения email"
    body = (
        f"Ваш код подтверждения: {code}\n\n"
        f"Код действителен {settings.EMAIL_VERIFY_CODE_TTL_SECONDS // 60} минут."
    )

    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV verification code for %s: %s", email, code)
        return code

    await _send_email(email, subject, body)
    return None


async def send_password_reset_email(email: str, reset_token: str) -> str | None:
    subject = "KWork Mob — сброс пароля"
    link = f"{settings.API_BASE_URL}/reset-password?token={reset_token}"
    body = f"Для сброса пароля перейдите по ссылке:\n{link}\n\nСсылка действительна 1 час."

    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV password reset for %s: token=%s", email, reset_token)
        return reset_token

    await _send_email(email, subject, body)
    return None


async def send_marketing_email(email: str, subject: str, body: str) -> None:
    """Маркетинговое письмо; в dev без SMTP — только лог."""
    footer = "\n\n---\nОтписаться от маркетинга: настройки профиля (marketing_opt_in)."
    full = body + footer
    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV marketing email → %s | %s | %s", email, subject, body[:200])
        return
    await _send_email(email, subject, full)


async def send_alert_email(email: str, subject: str, body: str) -> None:
    """Системный алерт владельцу (§12.4) — без marketing footer."""
    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV alert email → %s | %s | %s", email, subject, body[:300])
        return
    await _send_email(email, subject, body)


async def _send_email(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP не настроен")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)
