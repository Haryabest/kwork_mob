"""Статистика shoot-links §3.15.4 — created / expired / success per company."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ShootLink


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def expire_stale(db: AsyncSession, *, company_id: int | None = None) -> int:
    """Пометить просроченные active → expired."""
    now = datetime.now(timezone.utc)
    q = select(ShootLink).where(ShootLink.status == "active", ShootLink.expires_at < now)
    if company_id is not None:
        q = q.where(ShootLink.company_id == company_id)
    rows = (await db.scalars(q.limit(5000))).all()
    n = 0
    for row in rows:
        row.status = "expired"
        n += 1
    if n:
        await db.flush()
    return n


async def company_stats(db: AsyncSession, company_id: int) -> dict[str, Any]:
    """Количество созданных, истекших, успешных съёмок (§3.15.4)."""
    await expire_stale(db, company_id=company_id)
    rows = (
        await db.scalars(select(ShootLink).where(ShootLink.company_id == company_id).order_by(ShootLink.id.desc()))
    ).all()
    created = len(rows)
    active = sum(1 for r in rows if r.status == "active")
    expired = sum(1 for r in rows if r.status == "expired")
    # успешная съёмка: ссылка использована (used) или used_count > 0
    success = sum(1 for r in rows if r.status == "used" or (r.used_count or 0) > 0)
    revoked = sum(1 for r in rows if r.status == "revoked")
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    recent = [
        {
            "id": r.id,
            "token": r.token[:8] + "…",
            "task_uuid": r.task_uuid,
            "status": r.status,
            "used_count": r.used_count,
            "max_uses": r.max_uses,
            "category": r.category,
            "tier": r.tier,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows[:30]
    ]
    return {
        "company_id": company_id,
        "created": created,
        "active": active,
        "expired": expired,
        "success": success,
        "revoked": revoked,
        "by_status": by_status,
        "conversion_rate": round(success / created, 4) if created else 0.0,
        "recent": recent,
    }


async def admin_overview(db: AsyncSession, *, limit: int = 50) -> dict[str, Any]:
    """Сводка по всем B2B-клиентам для панели владельца сервиса."""
    await expire_stale(db)
    company_ids = (
        await db.scalars(
            select(ShootLink.company_id)
            .where(ShootLink.company_id.is_not(None))
            .group_by(ShootLink.company_id)
            .order_by(func.count().desc())
            .limit(limit)
        )
    ).all()
    items = []
    for cid in company_ids:
        if cid is None:
            continue
        items.append(await company_stats(db, int(cid)))
    from sqlalchemy import or_

    total_created = await db.scalar(select(func.count()).select_from(ShootLink))
    total_success = await db.scalar(
        select(func.count()).select_from(ShootLink).where(
            or_(ShootLink.status == "used", ShootLink.used_count > 0)
        )
    )
    total_expired = await db.scalar(
        select(func.count()).select_from(ShootLink).where(ShootLink.status == "expired")
    )
    return {
        "totals": {
            "created": int(total_created or 0),
            "success": int(total_success or 0),
            "expired": int(total_expired or 0),
        },
        "companies": items,
    }
