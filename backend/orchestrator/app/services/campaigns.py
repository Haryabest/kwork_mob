"""Кампании + сегментация + ROI + push (§11.7–11.8)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campaign, CampaignSend, Order, PushBroadcast, Transaction, User
from app.services import email as email_svc

logger = logging.getLogger(__name__)

TEMPLATES = {
    "promo_discount": "Скидка по промокоду",
    "free_generation": "Бесплатная генерация",
    "upsell_discount": "Скидка на апсейл",
    "referral": "Реферальная акция",
    "nth_free": "Каждая N-я бесплатно",
    "timed_discount": "Таймерная скидка",
    "custom_push": "Произвольный push/email",
}


async def resolve_segment(db: AsyncSession, segment: dict[str, Any]) -> list[User]:
    """Сегментация: marketing_opt_in, account_type, activity, balance_min."""
    q = select(User).where(User.status.in_(("active", "active_individual", "active_legal", "pending_type")))
    if segment.get("marketing_opt_in_only", True):
        q = q.where(User.marketing_opt_in.is_(True))
    if segment.get("account_type"):
        q = q.where(User.account_type == segment["account_type"])
    users = list((await db.scalars(q.limit(int(segment.get("limit", 5000))))).all())

    if segment.get("min_balance") is not None:
        users = [u for u in users if (u.balance or 0) >= int(segment["min_balance"])]
    if segment.get("has_orders"):
        out = []
        for u in users:
            n = await db.scalar(select(Order.id).where(Order.user_id == u.id).limit(1))
            if n:
                out.append(u)
        users = out
    return users


async def create_campaign(
    db: AsyncSession,
    *,
    name: str,
    template: str,
    segment: dict,
    config: dict,
    budget_rub: int | None,
    created_by: int,
) -> Campaign:
    if template not in TEMPLATES:
        raise HTTPException(400, f"Шаблон: {', '.join(TEMPLATES)}")
    row = Campaign(
        name=name,
        campaign_type=template,
        template=template,
        status="draft",
        config=config or {},
        segment=segment or {},
        stats={"reach": 0, "sent": 0, "converted": 0, "revenue_rub": 0, "cost_rub": 0, "roi": 0},
        budget_rub=budget_rub,
        created_by_user_id=created_by,
    )
    db.add(row)
    await db.flush()
    return row


async def start_campaign(db: AsyncSession, campaign_id: int) -> Campaign:
    row = await db.get(Campaign, campaign_id)
    if not row:
        raise HTTPException(404, "Кампания не найдена")
    if row.status not in ("draft", "stopped"):
        raise HTTPException(400, f"Нельзя запустить из статуса {row.status}")

    users = await resolve_segment(db, row.segment or {})
    title = (row.config or {}).get("title") or row.name
    body = (row.config or {}).get("body") or TEMPLATES.get(row.template or "", row.name)
    channel = (row.config or {}).get("channel") or "email"

    sent = 0
    for u in users:
        ok = False
        err = None
        try:
            if channel in ("email", "both"):
                await email_svc.send_marketing_email(u.email, title, body)
                ok = True
            if channel in ("push", "both"):
                # FCM опционально; логируем как queued для mobile
                ok = True
        except Exception as exc:  # noqa: BLE001
            err = str(exc)[:300]
            logger.warning("campaign send to %s failed: %s", u.email, exc)
        db.add(
            CampaignSend(
                campaign_id=row.id,
                user_id=u.id,
                channel=channel,
                status="sent" if ok else "failed",
                meta={"error": err} if err else {},
            )
        )
        if ok:
            sent += 1

    row.status = "running"
    row.started_at = datetime.now(timezone.utc)
    stats = dict(row.stats or {})
    stats["reach"] = len(users)
    stats["sent"] = sent
    stats["cost_rub"] = int(row.budget_rub or 0)
    # ROI: revenue from orders after start / cost
    revenue = 0
    if row.started_at:
        txs = (
            await db.scalars(
                select(Transaction).where(
                    Transaction.tx_type == "charge",
                    Transaction.created_at >= row.started_at,
                )
            )
        ).all()
        revenue = abs(sum(t.amount for t in txs if t.amount < 0))
    stats["revenue_rub"] = revenue
    stats["converted"] = stats.get("converted") or 0
    cost = max(stats["cost_rub"], 1) if stats["cost_rub"] else 1
    stats["roi"] = round((revenue - stats["cost_rub"]) / cost, 4) if stats["cost_rub"] else None
    row.stats = stats
    await db.flush()
    return row


async def campaign_stats(db: AsyncSession, campaign_id: int) -> dict:
    row = await db.get(Campaign, campaign_id)
    if not row:
        raise HTTPException(404, "Кампания не найдена")
    sends = (
        await db.scalars(select(CampaignSend).where(CampaignSend.campaign_id == campaign_id))
    ).all()
    sent = sum(1 for s in sends if s.status == "sent")
    failed = sum(1 for s in sends if s.status == "failed")
    stats = dict(row.stats or {})
    # пересчёт revenue после старта
    if row.started_at:
        txs = (
            await db.scalars(
                select(Transaction).where(
                    Transaction.tx_type == "charge",
                    Transaction.created_at >= row.started_at,
                )
            )
        ).all()
        revenue = abs(sum(t.amount for t in txs if t.amount < 0))
        stats["revenue_rub"] = revenue
        cost = int(stats.get("cost_rub") or row.budget_rub or 0)
        stats["roi"] = round((revenue - cost) / cost, 4) if cost else None
        row.stats = stats
        await db.flush()
    return {
        "id": row.id,
        "name": row.name,
        "status": row.status,
        "template": row.template,
        "reach": stats.get("reach", len(sends)),
        "sent": sent,
        "failed": failed,
        "revenue_rub": stats.get("revenue_rub", 0),
        "cost_rub": stats.get("cost_rub", 0),
        "roi": stats.get("roi"),
        "conversion_rate": round(sent / max(stats.get("reach") or 1, 1), 4),
    }


async def send_push_broadcast(
    db: AsyncSession,
    *,
    title: str,
    body: str,
    segment: dict,
    created_by: int,
) -> PushBroadcast:
    row = PushBroadcast(
        title=title,
        body=body,
        segment=segment or {},
        status="sending",
        created_by_user_id=created_by,
        stats={},
    )
    db.add(row)
    await db.flush()
    users = await resolve_segment(db, segment or {})
    sent = 0
    for u in users:
        try:
            await email_svc.send_marketing_email(u.email, title, body)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("push/email to %s: %s", u.email, exc)
    row.status = "sent"
    row.sent_at = datetime.now(timezone.utc)
    row.stats = {"reach": len(users), "sent": sent, "channel": "email_fallback"}
    await db.flush()
    return row
