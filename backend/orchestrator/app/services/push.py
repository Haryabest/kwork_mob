"""FCM push + email fallback (§3.4.3 / §11.8).

Конфиг (.env):
  FCM_SERVER_KEY=...                 # legacy HTTP API
  FCM_SERVICE_ACCOUNT_JSON=/path.json  # HTTP v1 (предпочтительно)
  FCM_PROJECT_ID=...
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import DeviceToken, User

logger = logging.getLogger(__name__)


def _fcm_configured() -> bool:
    return bool(settings.FCM_SERVER_KEY or settings.FCM_SERVICE_ACCOUNT_JSON)


def _access_token_v1() -> tuple[str, str] | None:
    """(access_token, project_id) из service account JSON."""
    path = (settings.FCM_SERVICE_ACCOUNT_JSON or "").strip()
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        logger.error("FCM_SERVICE_ACCOUNT_JSON not found: %s", path)
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            str(p),
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        creds.refresh(Request())
        data = json.loads(p.read_text(encoding="utf-8"))
        project_id = settings.FCM_PROJECT_ID or data.get("project_id") or ""
        if not project_id or not creds.token:
            return None
        return creds.token, project_id
    except Exception as exc:  # noqa: BLE001
        logger.warning("FCM v1 auth failed: %s", exc)
        return None


def send_fcm_to_token(token: str, title: str, body: str, data: dict[str, str] | None = None) -> dict[str, Any]:
    """Синхронная отправка на один токен. Возвращает {ok, channel, detail}."""
    data = data or {}
    v1 = _access_token_v1()
    if v1:
        access, project_id = v1
        url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        payload = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                "data": {k: str(v) for k, v in data.items()},
                "android": {"priority": "HIGH"},
                "apns": {"headers": {"apns-priority": "10"}},
            }
        }
        with httpx.Client(timeout=20.0) as client:
            r = client.post(url, headers={"Authorization": f"Bearer {access}"}, json=payload)
        ok = r.status_code < 300
        return {"ok": ok, "channel": "fcm_v1", "status": r.status_code, "detail": r.text[:500]}

    key = (settings.FCM_SERVER_KEY or "").strip()
    if not key:
        return {"ok": False, "channel": "none", "detail": "FCM not configured"}

    # Legacy HTTP
    with httpx.Client(timeout=20.0) as client:
        r = client.post(
            "https://fcm.googleapis.com/fcm/send",
            headers={"Authorization": f"key={key}", "Content-Type": "application/json"},
            json={
                "to": token,
                "priority": "high",
                "notification": {"title": title, "body": body},
                "data": data,
            },
        )
    ok = r.status_code < 300
    return {"ok": ok, "channel": "fcm_legacy", "status": r.status_code, "detail": r.text[:500]}


async def send_to_user(
    db: AsyncSession,
    user_id: int,
    title: str,
    body: str,
    *,
    data: dict[str, str] | None = None,
    email_fallback: bool = True,
) -> dict[str, Any]:
    """Push на все устройства пользователя; при неудаче — email (§3.4.3)."""
    tokens = (
        await db.scalars(select(DeviceToken).where(DeviceToken.user_id == user_id))
    ).all()
    results: list[dict] = []
    delivered = False
    for t in tokens:
        res = send_fcm_to_token(t.token, title, body, data)
        results.append({"token_suffix": t.token[-8:], "platform": t.platform, **res})
        if res.get("ok"):
            delivered = True

    email_sent = False
    if not delivered and email_fallback:
        user = await db.get(User, user_id)
        if user and user.email:
            try:
                from app.services import email as email_svc

                await email_svc.send_marketing_email(user.email, title, body)
                email_sent = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("email fallback user=%s: %s", user_id, exc)

    return {
        "user_id": user_id,
        "fcm_configured": _fcm_configured(),
        "devices": len(tokens),
        "delivered_push": delivered,
        "email_fallback": email_sent,
        "results": results,
    }


async def send_to_users(
    db: AsyncSession,
    user_ids: list[int],
    title: str,
    body: str,
    *,
    data: dict[str, str] | None = None,
) -> dict[str, Any]:
    pushed = 0
    emailed = 0
    details = []
    for uid in user_ids:
        r = await send_to_user(db, uid, title, body, data=data, email_fallback=True)
        details.append(r)
        if r["delivered_push"]:
            pushed += 1
        elif r["email_fallback"]:
            emailed += 1
    return {
        "reach": len(user_ids),
        "pushed": pushed,
        "emailed": emailed,
        "fcm_configured": _fcm_configured(),
        "details": details[:50],
    }
