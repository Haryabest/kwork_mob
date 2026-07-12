"""B2B webhooks §4.8.7: model.generated, order.created, order.failed, balance.low."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CompanyWebhook, CompanyWebhookDelivery
from app.services.company_members import get_owned_company

logger = logging.getLogger(__name__)

EVENTS = {
    "model.generated",
    "order.created",
    "order.failed",
    "order.completed",
    "balance.low",
    "member.invited",
}


async def create_webhook(
    db: AsyncSession,
    user,
    *,
    url: str,
    events: list[str],
    secret: str,
) -> CompanyWebhook:
    company = await get_owned_company(db, user)
    ev = [e for e in events if e in EVENTS]
    if not ev:
        raise HTTPException(400, f"events из: {', '.join(sorted(EVENTS))}")
    if not url.startswith("https://") and not url.startswith("http://localhost"):
        raise HTTPException(400, "URL должен быть https:// (или localhost для dev)")
    row = CompanyWebhook(
        company_id=company.id,
        url=url,
        secret=secret,
        events=ev,
        is_active=True,
    )
    db.add(row)
    await db.flush()
    return row


async def list_webhooks(db: AsyncSession, user) -> list[dict]:
    company = await get_owned_company(db, user)
    rows = (
        await db.scalars(
            select(CompanyWebhook).where(CompanyWebhook.company_id == company.id).order_by(CompanyWebhook.id.desc())
        )
    ).all()
    return [
        {
            "id": w.id,
            "url": w.url,
            "events": w.events,
            "is_active": w.is_active,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in rows
    ]


async def delete_webhook(db: AsyncSession, user, webhook_id: int) -> None:
    company = await get_owned_company(db, user)
    row = await db.get(CompanyWebhook, webhook_id)
    if not row or row.company_id != company.id:
        raise HTTPException(404, "Webhook не найден")
    row.is_active = False
    await db.flush()


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def emit(db: AsyncSession, *, company_id: int | None, event: str, payload: dict) -> int:
    if not company_id or event not in EVENTS:
        return 0
    hooks = (
        await db.scalars(
            select(CompanyWebhook).where(
                CompanyWebhook.company_id == company_id,
                CompanyWebhook.is_active.is_(True),
            )
        )
    ).all()
    sent = 0
    body_obj = {
        "event": event,
        "company_id": company_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    raw = json.dumps(body_obj, ensure_ascii=False, separators=(",", ":")).encode()
    async with httpx.AsyncClient(timeout=10.0) as client:
        for h in hooks:
            if event not in (h.events or []):
                continue
            sig = _sign(h.secret or "", raw)
            ok = False
            err = None
            status_code = None
            try:
                resp = await client.post(
                    h.url,
                    content=raw,
                    headers={
                        "Content-Type": "application/json",
                        "X-KWork-Event": event,
                        "X-KWork-Signature": sig,
                    },
                )
                status_code = resp.status_code
                ok = 200 <= resp.status_code < 300
                if not ok:
                    err = resp.text[:300]
            except Exception as exc:  # noqa: BLE001
                err = str(exc)[:300]
                logger.warning("webhook %s → %s failed: %s", h.id, h.url, exc)
            db.add(
                CompanyWebhookDelivery(
                    webhook_id=h.id,
                    event=event,
                    payload=body_obj,
                    ok=ok,
                    status_code=status_code,
                    error=err,
                )
            )
            if ok:
                sent += 1
    await db.flush()
    return sent
