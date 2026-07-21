"""Rate limit создания заказов: не более N/час (§10.10)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Company, Order


async def assert_order_creation_allowed(
    db: AsyncSession,
    *,
    user_id: int,
    company_id: int | None = None,
) -> None:
    limit = max(1, int(settings.ORDERS_PER_HOUR_LIMIT or 10))
    if company_id:
        company = await db.get(Company, company_id)
        if company:
            cfg = dict(company.settings or {})
            if cfg.get("premium_order_limit"):
                limit = max(limit, int(cfg.get("orders_per_hour_limit", limit * 2)))

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.user_id == user_id,
            Order.created_at >= since,
        )
    )
    if int(count or 0) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "order_rate_limit",
                "message": f"Не более {limit} заказов в час с одного аккаунта (§10.10)",
                "limit": limit,
                "window_hours": 1,
            },
        )
