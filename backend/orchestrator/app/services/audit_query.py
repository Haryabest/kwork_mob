"""Admin audit_log queries §2.2.3 / §10.7.7."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog

OAUTH_AUDIT_ACTIONS = ("oauth_login", "oauth_link", "oauth_unlink")


async def list_audit_logs(
    db: AsyncSession,
    *,
    action: str | None = None,
    action_prefix: str | None = None,
    user_id: int | None = None,
    days: int = 30,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    filters = [AuditLog.created_at >= since]
    if action:
        filters.append(AuditLog.action == action)
    elif action_prefix:
        filters.append(AuditLog.action.like(f"{action_prefix}%"))
    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)

    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    rows = (
        await db.scalars(
            select(AuditLog).where(*filters).order_by(AuditLog.id.desc()).offset(offset).limit(limit)
        )
    ).all()
    return {
        "total": int(total or 0),
        "days": days,
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "company_id": r.company_id,
                "action": r.action,
                "details": r.details,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


async def oauth_audit_summary(db: AsyncSession, *, days: int = 7) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    counts: dict[str, int] = {}
    for action in OAUTH_AUDIT_ACTIONS:
        n = await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.created_at >= since, AuditLog.action == action)
        )
        counts[action] = int(n or 0)
    return {
        "days": days,
        "oauth_login": counts["oauth_login"],
        "oauth_link": counts["oauth_link"],
        "oauth_unlink": counts["oauth_unlink"],
        "total": sum(counts.values()),
    }
