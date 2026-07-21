"""B2B API key usage metrics §11.5."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, CompanyApiKey, Order


async def summary(db: AsyncSession, *, days: int = 7) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    keys = (await db.scalars(select(CompanyApiKey).where(CompanyApiKey.is_active.is_(True)))).all()
    by_company: dict[int, dict] = {}
    for k in keys:
        slot = by_company.setdefault(
            k.company_id,
            {
                "company_id": k.company_id,
                "active_keys": 0,
                "used_keys_7d": 0,
                "last_used_at": None,
            },
        )
        slot["active_keys"] += 1
        if k.last_used_at and k.last_used_at >= since:
            slot["used_keys_7d"] += 1
        if k.last_used_at:
            prev = slot["last_used_at"]
            cur = k.last_used_at.isoformat()
            if not prev or cur > prev:
                slot["last_used_at"] = cur

    order_rows = (
        await db.execute(
            select(Order.company_id, func.count(), func.coalesce(func.sum(Order.amount), 0))
            .where(Order.company_id.is_not(None), Order.created_at >= since)
            .group_by(Order.company_id)
        )
    ).all()
    orders_by_co = {int(r[0]): {"orders": int(r[1]), "revenue_rub": int(r[2])} for r in order_rows}

    if not by_company:
        return {"days": days, "total_active_keys": 0, "companies_with_keys": 0, "items": []}

    companies = (
        await db.scalars(select(Company).where(Company.id.in_(list(by_company.keys()) if by_company else [0])))
    ).all()
    names = {c.id: c.name for c in companies}

    items = []
    for cid, row in by_company.items():
        o = orders_by_co.get(cid, {"orders": 0, "revenue_rub": 0})
        items.append(
            {
                **row,
                "company_name": names.get(cid),
                "orders_7d": o["orders"],
                "revenue_7d_rub": o["revenue_rub"],
            }
        )
    items.sort(key=lambda x: (-x["used_keys_7d"], -x["orders_7d"]))
    return {
        "days": days,
        "total_active_keys": sum(i["active_keys"] for i in items),
        "companies_with_keys": len(items),
        "items": items[:100],
    }
