"""Email-шаблоны по языку §16.2.2."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.locale import normalize_locale

_TEMPLATES_ROOT = Path(__file__).resolve().parents[2] / "templates" / "email"


@lru_cache(maxsize=128)
def _load_file_pack(key: str, locale: str) -> dict[str, str] | None:
    path = _TEMPLATES_ROOT / locale / f"{key}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:  # noqa: BLE001
        return None
    return None

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
    "session_revoked": {
        "ru": {
            "subject": "3DVektor — вход с другого устройства",
            "body": "Выполнен вход в ваш аккаунт с другого устройства. Предыдущая сессия завершена.",
        },
        "en": {
            "subject": "3DVektor — sign-in from another device",
            "body": "Your account was signed in from another device. The previous session was ended.",
        },
        "kk": {
            "subject": "3DVektor — басқа құрылғыдан кіру",
            "body": "Аккаунтыңызға басқа құрылғыдан кіру орындалды. Алдыңғы сессия аяқталды.",
        },
        "zh-CN": {
            "subject": "3DVektor — 其他设备登录",
            "body": "您的账号在其他设备上登录，之前的会话已结束。",
        },
    },
}


def render_template(key: str, locale: str | None, **kwargs: Any) -> dict[str, str]:
    loc = normalize_locale(locale)
    pack = _TEMPLATES.get(key, {})
    tpl = _load_file_pack(key, loc) or pack.get(loc) or pack.get("ru") or {"subject": "", "body": ""}
    out = {k: v.format(**kwargs) for k, v in tpl.items()}
    out["locale"] = loc
    return out


def templates_root() -> Path:
    """§15.3 — каталог templates/{lang}/ на диске."""
    return _TEMPLATES_ROOT


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
