"""NSFW SLA escalate: просроченные >24ч → Telegram (§10.8)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlertLog, NsfwBlock, Order, User
from app.services import alerts as alerts_svc

logger = logging.getLogger(__name__)

SLA_HOURS = 24
COOLDOWN = timedelta(hours=6)
EVENT = "nsfw_sla_overdue"


async def _recently_alerted(db: AsyncSession, block_id: int) -> bool:
    since = datetime.now(timezone.utc) - COOLDOWN
    rows = (
        await db.scalars(
            select(AlertLog)
            .where(AlertLog.event_type == EVENT, AlertLog.ok.is_(True), AlertLog.created_at >= since)
            .order_by(AlertLog.id.desc())
            .limit(50)
        )
    ).all()
    for r in rows:
        if (r.payload or {}).get("block_id") == block_id:
            return True
    return False


async def escalate_overdue(db: AsyncSession) -> dict[str, Any]:
    """Celery: непроверенные NSFW-блоки старше 24ч → срочный dual-channel алерт."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=SLA_HOURS)
    rows = (
        await db.scalars(
            select(NsfwBlock)
            .where(NsfwBlock.verified.is_(False), NsfwBlock.created_at <= cutoff)
            .order_by(NsfwBlock.created_at)
            .limit(100)
        )
    ).all()
    sent = 0
    for b in rows:
        if await _recently_alerted(db, b.id):
            continue
        order = await db.get(Order, b.order_id)
        user = await db.get(User, b.user_id)
        hours = round((now - (b.created_at or now).replace(tzinfo=timezone.utc)).total_seconds() / 3600, 1)
        text = (
            f"🚨 NSFW SLA просрочен (>24ч)\n"
            f"block #{b.id} · order #{b.order_id}\n"
            f"user: {user.email if user else b.user_id}\n"
            f"reason: {b.reason}\n"
            f"overdue: {hours}ч · refunded={b.refunded}\n"
            f"task: {order.task_uuid if order else '—'}"
        )
        dual = await alerts_svc.send_dual(
            db,
            text,
            event_type=EVENT,
            payload={
                "block_id": b.id,
                "order_id": b.order_id,
                "user_id": b.user_id,
                "hours_overdue": hours,
            },
            subject=f"[3dvektor] NSFW SLA overdue block=#{b.id}",
        )
        if dual.get("telegram") or dual.get("email"):
            sent += 1
    await db.commit()
    return {"overdue": len(rows), "alerts_sent": sent}
