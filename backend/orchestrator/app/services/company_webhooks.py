"""B2B webhooks §4.8.7 / §14.5.4: HMAC, retry ×10, DLQ, alert после 3 fails (ERP)."""

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
    """После 3 подряд fail — email + Telegram Owner компании (§14.5.4 / ERP webhooks)."""
    from app.core.config import settings

    streak = int(getattr(settings, "COMPANY_WEBHOOK_FAIL_STREAK", 3) or 3)
    if delivery.attempt < streak:
        return
    recent = (
        await db.scalars(
            select(CompanyWebhookDelivery)
            .where(CompanyWebhookDelivery.webhook_id == hook.id)
            .order_by(CompanyWebhookDelivery.id.desc())
            .limit(streak)
        )
    ).all()
    if len(recent) < streak or any(r.ok for r in recent):
        return
    from app.models import Company, User
    from app.services import alerts as alerts_svc

    company = await db.get(Company, hook.company_id)
    if not company:
        return
    owner = await db.get(User, company.owner_id)
    msg = (
        f"Webhook #{hook.id} ({hook.url}) failed {streak} times. "
        f"Last error: {delivery.error}"
    )
    # dual-channel владельцу сервиса + письмо Owner компании
    try:
        await alerts_svc.send_dual(
            db,
            f"🔔 Company webhook failures ×{streak}\ncompany #{hook.company_id}\n{msg}",
            event_type="webhook_failures",
            payload={
                "fingerprint": f"cwh:{hook.id}:{delivery.id // max(streak, 1)}",
                "webhook_id": hook.id,
                "company_id": hook.company_id,
                "delivery_id": delivery.id,
                "streak": streak,
            },
            subject=f"[3dvektor] Webhook failures company={hook.company_id}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("webhook alert dual: %s", exc)
    if owner and owner.email:
        try:
            from app.services import email as email_svc

            await email_svc.send_marketing_email(owner.email, "Webhook delivery failures", msg)
        except Exception as exc:  # noqa: BLE001
            logger.warning("webhook alert owner email: %s", exc)


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
            "payload": r.payload,
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


async def replay_dlq(db: AsyncSession, user, *, limit: int = 50) -> dict:
    """Массовый replay всех DLQ доставок компании."""
    company = await get_owned_company(db, user)
    hook_ids = (
        await db.scalars(select(CompanyWebhook.id).where(CompanyWebhook.company_id == company.id))
    ).all()
    if not hook_ids:
        return {"replayed": 0, "delivered": 0, "failed": 0}
    rows = (
        await db.scalars(
            select(CompanyWebhookDelivery)
            .where(
                CompanyWebhookDelivery.webhook_id.in_(list(hook_ids)),
                CompanyWebhookDelivery.status == "dlq",
            )
            .order_by(CompanyWebhookDelivery.id.desc())
            .limit(limit)
        )
    ).all()
    delivered = 0
    failed = 0
    for d in rows:
        result = await retry_delivery(db, user, d.id)
        if result.get("status") == "delivered":
            delivered += 1
        else:
            failed += 1
    return {"replayed": len(rows), "delivered": delivered, "failed": failed}


async def get_delivery(db: AsyncSession, user, delivery_id: int) -> dict:
    company = await get_owned_company(db, user)
    d = await db.get(CompanyWebhookDelivery, delivery_id)
    if not d:
        raise HTTPException(404, "Delivery не найден")
    hook = await db.get(CompanyWebhook, d.webhook_id)
    if not hook or hook.company_id != company.id:
        raise HTTPException(404, "Delivery не найден")
    return {
        "id": d.id,
        "webhook_id": d.webhook_id,
        "event": d.event,
        "ok": d.ok,
        "status": d.status,
        "attempt": d.attempt,
        "max_attempts": d.max_attempts,
        "status_code": d.status_code,
        "error": d.error,
        "payload": d.payload,
        "next_retry_at": d.next_retry_at.isoformat() if d.next_retry_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


async def delivery_dashboard(db: AsyncSession, *, company_id: int | None = None, limit: int = 100) -> dict:
    """Admin/seller summary: pending retries, DLQ, success rate (§14.5.4)."""
    from sqlalchemy import func

    from app.models import Company

    q_hooks = select(CompanyWebhook)
    if company_id:
        q_hooks = q_hooks.where(CompanyWebhook.company_id == company_id)
    hooks = (await db.scalars(q_hooks)).all()
    hook_ids = [h.id for h in hooks]
    if not hook_ids:
        return {
            "pending": 0,
            "dlq": 0,
            "delivered_24h": 0,
            "failed_streak_hooks": 0,
            "success_rate_24h": 1.0,
            "items": [],
            "by_status": {},
        }

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    pending = int(
        await db.scalar(
            select(func.count())
            .select_from(CompanyWebhookDelivery)
            .where(
                CompanyWebhookDelivery.webhook_id.in_(hook_ids),
                CompanyWebhookDelivery.status == "pending",
            )
        )
        or 0
    )
    dlq = int(
        await db.scalar(
            select(func.count())
            .select_from(CompanyWebhookDelivery)
            .where(
                CompanyWebhookDelivery.webhook_id.in_(hook_ids),
                CompanyWebhookDelivery.status == "dlq",
            )
        )
        or 0
    )
    delivered_24h = int(
        await db.scalar(
            select(func.count())
            .select_from(CompanyWebhookDelivery)
            .where(
                CompanyWebhookDelivery.webhook_id.in_(hook_ids),
                CompanyWebhookDelivery.status == "delivered",
                CompanyWebhookDelivery.created_at >= since,
            )
        )
        or 0
    )
    total_24h = int(
        await db.scalar(
            select(func.count())
            .select_from(CompanyWebhookDelivery)
            .where(
                CompanyWebhookDelivery.webhook_id.in_(hook_ids),
                CompanyWebhookDelivery.created_at >= since,
            )
        )
        or 0
    )
    by_status_rows = (
        await db.execute(
            select(CompanyWebhookDelivery.status, func.count())
            .where(CompanyWebhookDelivery.webhook_id.in_(hook_ids))
            .group_by(CompanyWebhookDelivery.status)
        )
    ).all()
    by_status = {str(s): int(c) for s, c in by_status_rows}

    # recent pending/dlq for dashboard table
    recent = (
        await db.scalars(
            select(CompanyWebhookDelivery)
            .where(
                CompanyWebhookDelivery.webhook_id.in_(hook_ids),
                CompanyWebhookDelivery.status.in_(("pending", "dlq")),
            )
            .order_by(CompanyWebhookDelivery.id.desc())
            .limit(limit)
        )
    ).all()
    hook_map = {h.id: h for h in hooks}
    company_ids = {h.company_id for h in hooks}
    companies = {}
    if company_ids:
        for c in (
            await db.scalars(select(Company).where(Company.id.in_(list(company_ids))))
        ).all():
            companies[c.id] = c.name

    items = []
    for r in recent:
        h = hook_map.get(r.webhook_id)
        items.append(
            {
                "id": r.id,
                "webhook_id": r.webhook_id,
                "company_id": h.company_id if h else None,
                "company_name": companies.get(h.company_id) if h else None,
                "url": h.url if h else None,
                "event": r.event,
                "status": r.status,
                "attempt": r.attempt,
                "max_attempts": r.max_attempts,
                "error": r.error,
                "next_retry_at": r.next_retry_at.isoformat() if r.next_retry_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )

    return {
        "pending": pending,
        "dlq": dlq,
        "delivered_24h": delivered_24h,
        "total_24h": total_24h,
        "success_rate_24h": round(delivered_24h / total_24h, 4) if total_24h else 1.0,
        "hooks_active": sum(1 for h in hooks if h.is_active),
        "by_status": by_status,
        "items": items,
        "as_of": now.isoformat(),
    }
