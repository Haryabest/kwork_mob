"""NSFW SLA dashboard metrics §10.8 / §11 — 24ч ручная проверка."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, NsfwBlock

SLA_HOURS = 24
URGENT_HOURS = 6


def _aware(dt: datetime | None, now: datetime) -> datetime:
    if dt is None:
        return now
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def sla_fields(created_at: datetime | None, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    created = _aware(created_at, now)
    deadline = created + timedelta(hours=SLA_HOURS)
    left_sec = (deadline - now).total_seconds()
    hours_left = round(left_sec / 3600, 2)
    return {
        "created_at": created.isoformat(),
        "deadline_at": deadline.isoformat(),
        "hours_left": hours_left,
        "hours_overdue": round(max(0.0, -hours_left), 2),
        "overdue": left_sec < 0,
        "urgent": 0 <= hours_left <= URGENT_HOURS,
        "sla_hours": SLA_HOURS,
    }


async def sla_dashboard(db: AsyncSession) -> dict[str, Any]:
    """Сводка очереди модерации для дашборда."""
    now = datetime.now(timezone.utc)
    pending_rows = (
        await db.scalars(
            select(NsfwBlock).where(NsfwBlock.verified.is_(False)).order_by(NsfwBlock.created_at.asc())
        )
    ).all()

    overdue = 0
    urgent = 0
    within = 0
    hours_left_vals: list[float] = []
    oldest_hours = 0.0
    queue_items: list[dict[str, Any]] = []

    for b in pending_rows:
        fields = sla_fields(b.created_at, now=now)
        hours_left_vals.append(float(fields["hours_left"]))
        age_h = round(
            (now - _aware(b.created_at, now)).total_seconds() / 3600,
            2,
        )
        oldest_hours = max(oldest_hours, age_h)
        if fields["overdue"]:
            overdue += 1
        elif fields["urgent"]:
            urgent += 1
            within += 1
        else:
            within += 1
        queue_items.append(
            {
                "id": b.id,
                "order_id": b.order_id,
                "user_id": b.user_id,
                "reason": b.reason,
                "refunded": b.refunded,
                **fields,
                "age_hours": age_h,
            }
        )

    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    verified_24h = int(
        await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action.in_(("nsfw_false_positive", "nsfw_confirmed_violation")),
                AuditLog.created_at >= since_24h,
            )
        )
        or 0
    )
    verified_7d = int(
        await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action.in_(("nsfw_false_positive", "nsfw_confirmed_violation")),
                AuditLog.created_at >= since_7d,
            )
        )
        or 0
    )
    total_verified = int(
        await db.scalar(select(func.count()).select_from(NsfwBlock).where(NsfwBlock.verified.is_(True)))
        or 0
    )
    total_blocks = int(await db.scalar(select(func.count()).select_from(NsfwBlock)) or 0)

    # SLA met: verified blocks whose created→verify ≤24h (approx via audit details)
    met = 0
    miss = 0
    audits = (
        await db.scalars(
            select(AuditLog)
            .where(AuditLog.action.in_(("nsfw_false_positive", "nsfw_confirmed_violation")))
            .order_by(AuditLog.id.desc())
            .limit(200)
        )
    ).all()
    for a in audits:
        details = a.details or {}
        block_id = details.get("block_id")
        if not block_id:
            continue
        block = await db.get(NsfwBlock, int(block_id))
        if not block or not block.created_at:
            continue
        created = _aware(block.created_at, now)
        verified_at = _aware(a.created_at, now)
        if (verified_at - created) <= timedelta(hours=SLA_HOURS):
            met += 1
        else:
            miss += 1
    sampled = met + miss
    sla_met_rate = round(met / sampled, 4) if sampled else 1.0

    avg_left = round(sum(hours_left_vals) / len(hours_left_vals), 2) if hours_left_vals else None

    # overdue first in queue preview
    queue_items.sort(key=lambda x: (not x["overdue"], x["hours_left"]))

    return {
        "sla_hours": SLA_HOURS,
        "urgent_hours": URGENT_HOURS,
        "pending": len(pending_rows),
        "overdue": overdue,
        "urgent": urgent,
        "within_sla": within,
        "avg_hours_left": avg_left,
        "oldest_pending_hours": oldest_hours if pending_rows else None,
        "verified_24h": verified_24h,
        "verified_7d": verified_7d,
        "total_verified": total_verified,
        "total_blocks": total_blocks,
        "sla_met": met,
        "sla_missed": miss,
        "sla_met_rate": sla_met_rate,
        "sla_ok": overdue == 0,
        "queue": queue_items[:50],
        "as_of": now.isoformat(),
    }
