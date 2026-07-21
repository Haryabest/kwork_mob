"""Отправка email (SMTP или dev-режим)."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.services import email_templates as tpl

logger = logging.getLogger(__name__)


async def send_verification_email(email: str, code: str, *, locale: str | None = None) -> str | None:
    """Отправляет 6-значный код. В dev возвращает код для отладки."""
    subject, body = tpl.verification_email(locale, code=code)

    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV verification code for %s: %s", email, code)
        return code

    await _send_email(email, subject, body)
    return None


async def send_password_reset_email(
    email: str, reset_token: str, *, locale: str | None = None
) -> str | None:
    subject, body = tpl.password_reset_email(locale, reset_token=reset_token)

    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV password reset for %s: token=%s", email, reset_token)
        return reset_token

    await _send_email(email, subject, body)
    return None


async def send_topup_failed_email(
    email: str, title: str, body: str, balance_url: str, *, locale: str | None = None
) -> None:
    """HTML fallback при payment.failed §3.4.3."""
    subj, plain, cta, loc = tpl.topup_failed_email(
        locale, title=title, body=body, balance_url=balance_url
    )
    html = _topup_failed_html(title=title, body=body, balance_url=balance_url, cta=cta, lang=loc)
    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV topup failed email → %s | %s | %s", email, subj, balance_url)
        return
    await _send_email(email, subj, plain, html_body=html)


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


async def send_notification_email(
    email: str, title: str, body: str, *, locale: str | None = None
) -> None:
    """Транзакционное уведомление (fallback push §3.4.3) — без marketing footer."""
    subject, plain = tpl.notification_email(locale, title=title, body=body)
    if settings.is_development and not settings.SMTP_HOST:
        logger.info("DEV notification email → %s | %s | %s", email, subject, plain[:300])
        return
    await _send_email(email, subject, plain)


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


def _topup_failed_html(
    *, title: str, body: str, balance_url: str, cta: str = "Balance", lang: str = "ru"
) -> str:
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;")
    safe_body = body.replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>")
    safe_url = balance_url.replace('"', "%22")
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="utf-8"/><title>{safe_title}</title></head>
<body style="font-family:system-ui,sans-serif;line-height:1.5;color:#1a1a1a;max-width:520px;margin:0 auto;padding:24px">
  <h2 style="margin:0 0 12px">{safe_title}</h2>
  <p style="margin:0 0 20px">{safe_body}</p>
  <p style="margin:0 0 24px">
    <a href="{safe_url}" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;
      padding:12px 20px;border-radius:8px;font-weight:600">{cta.replace("&", "&amp;").replace("<", "&lt;")}</a>
  </p>
  <p style="font-size:12px;color:#666;margin:0">3DVektor</p>
</body>
</html>"""
