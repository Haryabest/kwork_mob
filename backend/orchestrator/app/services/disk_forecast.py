"""Прогноз заполнения диска + wearout summary §23.7 / §11.16.5."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiskUsageSample
from app.services.minio import minio_service

SAMPLE_RETENTION_DAYS = 90


async def sample_disk_usage(db: AsyncSession) -> dict[str, Any]:
    """Celery: сохранить used/free % для тренда."""
    try:
        snap = minio_service.smart()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}
    used = snap.get("used_percent")
    free = snap.get("free_percent")
    total = snap.get("total_bytes")
    db.add(
        DiskUsageSample(
            used_percent=float(used) if used is not None else None,
            free_percent=float(free) if free is not None else None,
            total_bytes=int(total) if total is not None else None,
            sampled_at=datetime.now(timezone.utc),
        )
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=SAMPLE_RETENTION_DAYS)
    await db.execute(delete(DiskUsageSample).where(DiskUsageSample.sampled_at < cutoff))
    await db.commit()
    return {"ok": True, "used_percent": used, "free_percent": free}


async def disk_forecast(db: AsyncSession, *, days_lookback: int = 14) -> dict[str, Any]:
    """Линейный прогноз дней до 100% заполнения + wearout snapshot."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=max(1, min(days_lookback, 90)))
    rows = (
        await db.scalars(
            select(DiskUsageSample)
            .where(DiskUsageSample.sampled_at >= since, DiskUsageSample.used_percent.is_not(None))
            .order_by(DiskUsageSample.sampled_at.asc())
            .limit(2000)
        )
    ).all()

    samples = [
        {
            "sampled_at": r.sampled_at.isoformat() if r.sampled_at else None,
            "used_percent": r.used_percent,
            "free_percent": r.free_percent,
            "total_bytes": r.total_bytes,
        }
        for r in rows
    ]

    days_until_full = None
    growth_per_day = None
    current_used = None
    if len(rows) >= 2:
        first, last = rows[0], rows[-1]
        t0 = first.sampled_at or now
        t1 = last.sampled_at or now
        if t0.tzinfo is None:
            t0 = t0.replace(tzinfo=timezone.utc)
        if t1.tzinfo is None:
            t1 = t1.replace(tzinfo=timezone.utc)
        hours = max((t1 - t0).total_seconds() / 3600.0, 1.0)
        u0 = float(first.used_percent or 0)
        u1 = float(last.used_percent or 0)
        current_used = u1
        delta = u1 - u0
        growth_per_day = round(delta / (hours / 24.0), 4)
        if growth_per_day > 0.01:
            days_until_full = round((100.0 - u1) / growth_per_day, 1)
        elif growth_per_day <= 0:
            days_until_full = None  # shrinking or flat

    # live SMART wearout
    wearout: list[dict[str, Any]] = []
    try:
        snap = minio_service.smart()
        current_used = current_used if current_used is not None else snap.get("used_percent")
        for d in snap.get("smart_disks") or []:
            wear = d.get("wear_percent")
            if wear is None:
                wear = d.get("remaining_life_percent")
            wearout.append(
                {
                    "device": d.get("device") or d.get("model"),
                    "health": d.get("health"),
                    "wear_percent": wear,
                    "reallocated_sectors": d.get("reallocated_sectors"),
                    "temp_c": d.get("temp_c"),
                    "needs_replace": wear is not None and float(wear) < 15,
                    "bad_sectors": int(d.get("reallocated_sectors") or 0) > 0,
                }
            )
    except Exception:  # noqa: BLE001
        pass

    alert_fill = days_until_full is not None and days_until_full <= 30
    alert_wear = any(w.get("needs_replace") or w.get("bad_sectors") for w in wearout)

    return {
        "lookback_days": days_lookback,
        "samples": samples[-60:],
        "sample_count": len(samples),
        "current_used_percent": current_used,
        "growth_percent_per_day": growth_per_day,
        "days_until_full": days_until_full,
        "forecast_alert": alert_fill,
        "wearout": wearout,
        "wearout_alert": alert_wear,
        "as_of": now.isoformat(),
    }
