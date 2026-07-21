"""Email-шаблоны по языку §16.2.2."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.locale import normalize_locale

_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    "verification": {
        "ru": {
            "subject": "3DVektor — код подтверждения email",
            "body": "Ваш код подтверждения: {code}\n\nКод действителен {minutes} минут.",
        },
        "en": {
            "subject": "3DVektor — email verification code",
            "body": "Your verification code: {code}\n\nValid for {minutes} minutes.",
        },
        "kk": {
            "subject": "3DVektor — email растау коды",
            "body": "Растау кодыңыз: {code}\n\nКод {minutes} минут бойы жарамды.",
        },
        "zh-CN": {
            "subject": "3DVektor — 邮箱验证码",
            "body": "您的验证码：{code}\n\n有效期 {minutes} 分钟。",
        },
    },
    "password_reset": {
        "ru": {
            "subject": "3DVektor — сброс пароля",
            "body": "Для сброса пароля перейдите по ссылке:\n{link}\n\nСсылка действительна 1 час.",
        },
        "en": {
            "subject": "3DVektor — password reset",
            "body": "Reset your password:\n{link}\n\nLink valid for 1 hour.",
        },
        "kk": {
            "subject": "3DVektor — құпия сөзді қалпына келтіру",
            "body": "Құпия сөзді қалпына келтіру:\n{link}\n\nСілтеме 1 сағат жарамды.",
        },
        "zh-CN": {
            "subject": "3DVektor — 重置密码",
            "body": "请通过以下链接重置密码：\n{link}\n\n链接 1 小时内有效。",
        },
    },
    "notification": {
        "ru": {
            "subject": "{title}",
            "body": "{body}",
        },
        "en": {
            "subject": "{title}",
            "body": "{body}",
        },
        "kk": {
            "subject": "{title}",
            "body": "{body}",
        },
        "zh-CN": {
            "subject": "{title}",
            "body": "{body}",
        },
    },
    "topup_failed": {
        "ru": {
            "subject": "{title}",
            "body": "{body}\n\nОткрыть баланс: {balance_url}",
            "cta": "Открыть баланс",
        },
        "en": {
            "subject": "{title}",
            "body": "{body}\n\nOpen balance: {balance_url}",
            "cta": "Open balance",
        },
        "kk": {
            "subject": "{title}",
            "body": "{body}\n\nБалансты ашу: {balance_url}",
            "cta": "Балансты ашу",
        },
        "zh-CN": {
            "subject": "{title}",
            "body": "{body}\n\n打开余额：{balance_url}",
            "cta": "打开余额",
        },
    },
}


def render_template(key: str, locale: str | None, **kwargs: Any) -> dict[str, str]:
    loc = normalize_locale(locale)
    pack = _TEMPLATES.get(key, {})
    tpl = pack.get(loc) or pack.get("ru") or {"subject": "", "body": ""}
    out = {k: v.format(**kwargs) for k, v in tpl.items()}
    out["locale"] = loc
    return out


def verification_email(locale: str | None, *, code: str) -> tuple[str, str]:
    minutes = settings.EMAIL_VERIFY_CODE_TTL_SECONDS // 60
    data = render_template("verification", locale, code=code, minutes=minutes)
    return data["subject"], data["body"]


def password_reset_email(locale: str | None, *, reset_token: str) -> tuple[str, str]:
    link = f"{settings.API_BASE_URL}/reset-password?token={reset_token}"
    data = render_template("password_reset", locale, link=link)
    return data["subject"], data["body"]


def notification_email(locale: str | None, *, title: str, body: str) -> tuple[str, str]:
    data = render_template("notification", locale, title=title, body=body)
    return data["subject"], data["body"]


def topup_failed_email(
    locale: str | None, *, title: str, body: str, balance_url: str
) -> tuple[str, str, str, str]:
    data = render_template("topup_failed", locale, title=title, body=body, balance_url=balance_url)
    return data["subject"], data["body"], data.get("cta", "Balance"), data["locale"]
