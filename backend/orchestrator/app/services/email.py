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


async def send_topup_failed_email(email: str, title: str, body: str, balance_url: str) -> None:
    """HTML fallback при payment.failed §3.4.3."""
    html = _topup_failed_html(title=title, body=body, balance_url=balance_url)
    plain = f"{body}\n\nОткрыть баланс: {balance_url}"
    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV topup failed email → %s | %s | %s", email, title, balance_url)
        return
    await _send_email(email, title, plain, html_body=html)


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


async def send_notification_email(email: str, subject: str, body: str) -> None:
    """Транзакционное уведомление (fallback push §3.4.3) — без marketing footer."""
    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV notification email → %s | %s | %s", email, subject, body[:300])
        return
    await _send_email(email, subject, body)


async def _send_email(to: str, subject: str, body: str, *, html_body: str | None = None) -> None:
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP не настроен")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)


def _topup_failed_html(*, title: str, body: str, balance_url: str) -> str:
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;")
    safe_body = body.replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>")
    safe_url = balance_url.replace('"', "%22")
    return f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"/><title>{safe_title}</title></head>
<body style="font-family:system-ui,sans-serif;line-height:1.5;color:#1a1a1a;max-width:520px;margin:0 auto;padding:24px">
  <h2 style="margin:0 0 12px">{safe_title}</h2>
  <p style="margin:0 0 20px">{safe_body}</p>
  <p style="margin:0 0 24px">
    <a href="{safe_url}" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;
      padding:12px 20px;border-radius:8px;font-weight:600">Открыть баланс</a>
  </p>
  <p style="font-size:12px;color:#666;margin:0">KWork Mob · §20.3.4</p>
</body>
</html>"""
