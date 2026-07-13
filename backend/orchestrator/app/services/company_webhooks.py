"""B2B webhooks §4.8.7 / §14.5.4: HMAC, retry ×10, DLQ, alert после 3 fails."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

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
    "order.cancelled",
    "shoot_link.uploaded",
    "balance.low",
    "member.invited",
}

MAX_ATTEMPTS = 10


def _backoff_seconds(attempt: int) -> int:
    # 1,2,4,8,16,32,64,128,256,512 мин → cap 60 мин для prod cadence
    return min(60, 2 ** max(attempt - 1, 0)) * 60


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


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


async def _deliver_once(hook: CompanyWebhook, delivery: CompanyWebhookDelivery) -> bool:
    raw = json.dumps(delivery.payload, ensure_ascii=False, separators=(",", ":")).encode()
    sig = _sign(hook.secret or "", raw)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                hook.url,
                content=raw,
                headers={
                    "Content-Type": "application/json",
                    "X-KWork-Event": delivery.event,
                    "X-KWork-Signature": sig,
                    "X-KWork-Delivery": str(delivery.id),
                },
            )
        delivery.status_code = resp.status_code
        delivery.ok = 200 <= resp.status_code < 300
        if not delivery.ok:
            delivery.error = (resp.text or "")[:300]
        return delivery.ok
    except Exception as exc:  # noqa: BLE001
        delivery.error = str(exc)[:300]
        delivery.ok = False
        logger.warning("webhook %s attempt %s: %s", hook.id, delivery.attempt, exc)
        return False


async def emit(db: AsyncSession, *, company_id: int | None, event: str, payload: dict) -> int:
    """Создаёт delivery + первая попытка; при fail — retry schedule (§14.5.4)."""
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
    for h in hooks:
        if event not in (h.events or []):
            continue
        delivery = CompanyWebhookDelivery(
            webhook_id=h.id,
            event=event,
            payload=body_obj,
            attempt=1,
            max_attempts=MAX_ATTEMPTS,
            status="pending",
        )
        db.add(delivery)
        await db.flush()
        ok = await _deliver_once(h, delivery)
        if ok:
            delivery.status = "delivered"
            sent += 1
        else:
            if delivery.attempt >= delivery.max_attempts:
                delivery.status = "dlq"
            else:
                delivery.status = "pending"
                delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(
                    seconds=_backoff_seconds(delivery.attempt)
                )
            await _maybe_alert_owner(db, h, delivery)
    await db.flush()
    return sent


async def _maybe_alert_owner(db: AsyncSession, hook: CompanyWebhook, delivery: CompanyWebhookDelivery) -> None:
    """После 3 подряд fail — email Owner (§14.5.4)."""
    if delivery.attempt < 3:
        return
    recent = (
        await db.scalars(
            select(CompanyWebhookDelivery)
            .where(CompanyWebhookDelivery.webhook_id == hook.id)
            .order_by(CompanyWebhookDelivery.id.desc())
            .limit(3)
        )
    ).all()
    if len(recent) < 3 or any(r.ok for r in recent):
        return
    from app.models import Company, User
    from app.services import email as email_svc

    company = await db.get(Company, hook.company_id)
    if not company:
        return
    owner = await db.get(User, company.owner_id)
    if not owner or not owner.email:
        return
    try:
        await email_svc.send_marketing_email(
            owner.email,
            "Webhook delivery failures",
            f"Webhook #{hook.id} ({hook.url}) failed 3 times. Last error: {delivery.error}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("webhook alert email: %s", exc)


async def process_retries(db: AsyncSession, limit: int = 50) -> dict:
    """Celery: доставить pending с next_retry_at <= now."""
    now = datetime.now(timezone.utc)
    rows = (
        await db.scalars(
            select(CompanyWebhookDelivery)
            .where(
                CompanyWebhookDelivery.status == "pending",
                CompanyWebhookDelivery.next_retry_at.is_not(None),
                CompanyWebhookDelivery.next_retry_at <= now,
            )
            .order_by(CompanyWebhookDelivery.next_retry_at)
            .limit(limit)
        )
    ).all()
    delivered = 0
    dlq = 0
    for d in rows:
        hook = await db.get(CompanyWebhook, d.webhook_id)
        if not hook or not hook.is_active:
            d.status = "dlq"
            dlq += 1
            continue
        d.attempt = int(d.attempt or 1) + 1
        ok = await _deliver_once(hook, d)
        if ok:
            d.status = "delivered"
            d.next_retry_at = None
            delivered += 1
        elif d.attempt >= (d.max_attempts or MAX_ATTEMPTS):
            d.status = "dlq"
            d.next_retry_at = None
            dlq += 1
            await _maybe_alert_owner(db, hook, d)
        else:
            d.status = "pending"
            d.next_retry_at = now + timedelta(seconds=_backoff_seconds(d.attempt))
            await _maybe_alert_owner(db, hook, d)
    await db.flush()
    return {"processed": len(rows), "delivered": delivered, "dlq": dlq}


async def list_deliveries(
    db: AsyncSession,
    user,
    *,
    status: str | None = None,
    webhook_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    company = await get_owned_company(db, user)
    hook_ids = (
        await db.scalars(select(CompanyWebhook.id).where(CompanyWebhook.company_id == company.id))
    ).all()
    if not hook_ids:
        return []
    q = select(CompanyWebhookDelivery).where(CompanyWebhookDelivery.webhook_id.in_(list(hook_ids)))
    if status:
        q = q.where(CompanyWebhookDelivery.status == status)
    if webhook_id:
        q = q.where(CompanyWebhookDelivery.webhook_id == webhook_id)
    rows = (await db.scalars(q.order_by(CompanyWebhookDelivery.id.desc()).limit(limit))).all()
    return [
        {
            "id": r.id,
            "webhook_id": r.webhook_id,
            "event": r.event,
            "ok": r.ok,
            "status": r.status,
            "attempt": r.attempt,
            "max_attempts": r.max_attempts,
            "status_code": r.status_code,
            "error": r.error,
            "next_retry_at": r.next_retry_at.isoformat() if r.next_retry_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


async def retry_delivery(db: AsyncSession, user, delivery_id: int) -> dict:
    company = await get_owned_company(db, user)
    d = await db.get(CompanyWebhookDelivery, delivery_id)
    if not d:
        raise HTTPException(404, "Delivery не найден")
    hook = await db.get(CompanyWebhook, d.webhook_id)
    if not hook or hook.company_id != company.id:
        raise HTTPException(404, "Delivery не найден")
    d.attempt = int(d.attempt or 0) + 1
    d.status = "pending"
    ok = await _deliver_once(hook, d)
    if ok:
        d.status = "delivered"
        d.next_retry_at = None
    elif d.attempt >= (d.max_attempts or MAX_ATTEMPTS):
        d.status = "dlq"
    else:
        d.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=_backoff_seconds(d.attempt))
    await db.flush()
    return {"id": d.id, "ok": d.ok, "status": d.status, "attempt": d.attempt}
