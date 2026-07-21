"""Метрики сегментации DeepLab/SAM для admin UI §11.2.5."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SegmentationEvent


async def dashboard_metrics(db: AsyncSession, *, days: int = 7) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    total = int(
        await db.scalar(
            select(func.count()).select_from(SegmentationEvent).where(SegmentationEvent.created_at >= since)
        )
        or 0
    )
    fallback = int(
        await db.scalar(
            select(func.count())
            .select_from(SegmentationEvent)
            .where(SegmentationEvent.created_at >= since, SegmentationEvent.fallback_used.is_(True))
        )
        or 0
    )
    failed = int(
        await db.scalar(
            select(func.count())
            .select_from(SegmentationEvent)
            .where(SegmentationEvent.created_at >= since, SegmentationEvent.failed.is_(True))
        )
        or 0
    )
    avg_conf = await db.scalar(
        select(func.avg(SegmentationEvent.avg_confidence)).where(
            SegmentationEvent.created_at >= since,
            SegmentationEvent.avg_confidence.isnot(None),
        )
    )
    device_rows = (
        await db.execute(
            select(
                SegmentationEvent.device_model,
                func.count().label("total"),
                func.sum(case((SegmentationEvent.fallback_used.is_(True), 1), else_=0)).label("fallback"),
                func.sum(case((SegmentationEvent.failed.is_(True), 1), else_=0)).label("failed"),
            )
            .where(SegmentationEvent.created_at >= since)
            .group_by(SegmentationEvent.device_model)
            .order_by(func.count().desc())
            .limit(20)
        )
    ).all()
    method_rows = (
        await db.execute(
            select(SegmentationEvent.method, func.count())
            .where(SegmentationEvent.created_at >= since, SegmentationEvent.method.isnot(None))
            .group_by(SegmentationEvent.method)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()
    daily = (
        await db.execute(
            select(
                func.date_trunc("day", SegmentationEvent.created_at).label("day"),
                func.count(),
                func.sum(case((SegmentationEvent.fallback_used.is_(True), 1), else_=0)),
            )
            .where(SegmentationEvent.created_at >= since)
            .group_by("day")
            .order_by("day")
        )
    ).all()

    fallback_rate = round(fallback / total, 4) if total else 0.0
    failed_rate = round(failed / total, 4) if total else 0.0

    return {
        "days": days,
        "total": total,
        "fallback_count": fallback,
        "failed_count": failed,
        "fallback_rate": fallback_rate,
        "failed_rate": failed_rate,
        "avg_confidence": round(float(avg_conf), 4) if avg_conf is not None else None,
        "by_device": [
            {
                "device_model": r[0],
                "total": int(r[1] or 0),
                "fallback": int(r[2] or 0),
                "failed": int(r[3] or 0),
            }
            for r in device_rows
        ],
        "by_method": [{"method": r[0], "count": int(r[1] or 0)} for r in method_rows],
        "daily": [
            {
                "day": r[0].date().isoformat() if r[0] else None,
                "total": int(r[1] or 0),
                "fallback": int(r[2] or 0),
            }
            for r in daily
        ],
    }
