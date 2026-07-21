"""§1.4 DoD metrics — измеримые критерии успеха (staging/prod)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Model3D, ModelFeedback, NsfwBlock, Order, SupportMessage, SupportRequest, TaskConflict, TaskQueue
from app.services import publication_funnel as funnel_svc


def _threshold(metric: str, value: float | int | None, *, pass_if: bool) -> dict[str, Any]:
    return {"metric": metric, "value": value, "pass": pass_if}


async def compute_dod_metrics(db: AsyncSession, *, days: int = 7) -> dict[str, Any]:
    days = max(1, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    funnel_payload = await funnel_svc.global_funnel(db, date_from=since, date_to=None)
    funnel = funnel_payload.get("funnel") or {}
    generated = float(funnel.get("generated") or 0)
    verified = float(funnel.get("verified") or 0)
    funnel_conv = verified / max(generated, 1)

    completed = int(
        await db.scalar(
            select(func.count()).select_from(Order).where(
                Order.created_at >= since, Order.status == "completed"
            )
        )
        or 0
    )
    failed = int(
        await db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.created_at >= since,
                Order.status.in_(("failed", "cancelled", "blocked_nsfw", "nsfw_blocked")),
            )
        )
        or 0
    )
    pipeline_total = completed + failed
    success_rate = completed / max(pipeline_total, 1)

    # время генерации: processing_started → updated_at для completed tasks
    gen_rows = (
        await db.execute(
            select(TaskQueue.processing_started_at, TaskQueue.updated_at).where(
                TaskQueue.status.in_(("completed", "processing")),
                TaskQueue.processing_started_at.isnot(None),
                TaskQueue.updated_at >= since,
            )
        )
    ).all()
    durations = []
    for started, ended in gen_rows:
        if started and ended and ended > started:
            durations.append((ended - started).total_seconds())
    durations.sort()
    p95_gen = durations[int(len(durations) * 0.95)] if durations else None
    p95_home_ok = p95_gen is not None and p95_gen <= 180
    p95_cloud_ok = p95_gen is not None and p95_gen <= 300

    cancel_n = int(
        await db.scalar(
            select(func.count()).select_from(Order).where(
                Order.created_at >= since, Order.status.like("%cancel%")
            )
        )
        or 0
    )
    total_orders = int(
        await db.scalar(select(func.count()).select_from(Order).where(Order.created_at >= since)) or 0
    )
    cancel_rate = cancel_n / max(total_orders, 1)

    models_total = int(
        await db.scalar(select(func.count()).select_from(Model3D).where(Model3D.created_at >= since)) or 0
    )
    models_watermarked = int(
        await db.scalar(
            select(func.count())
            .select_from(Model3D)
            .where(Model3D.created_at >= since, Model3D.watermark_hmac.isnot(None))
        )
        or 0
    )
    dwt_coverage = models_watermarked / max(models_total, 1)

    fb_rows = (
        await db.execute(
            select(ModelFeedback.rating, func.count())
            .where(ModelFeedback.created_at >= since)
            .group_by(ModelFeedback.rating)
        )
    ).all()
    fb_total = sum(int(c) for _, c in fb_rows)
    fb_high = sum(int(c) for r, c in fb_rows if int(r) >= 4)
    rating_45_rate = fb_high / max(fb_total, 1)

    nsfw_total = int(
        await db.scalar(select(func.count()).select_from(NsfwBlock).where(NsfwBlock.created_at >= since)) or 0
    )
    nsfw_false = int(
        await db.scalar(
            select(func.count()).select_from(NsfwBlock).where(
                NsfwBlock.created_at >= since, NsfwBlock.verified.is_(True)
            )
        )
        or 0
    )
    nsfw_false_rate = nsfw_false / max(nsfw_total, 1) if nsfw_total else 0.0

    redlock_conflicts = int(
        await db.scalar(
            select(func.count()).select_from(TaskConflict).where(TaskConflict.created_at >= since)
        )
        or 0
    )

    hourly = (
        await db.execute(
            select(func.date_trunc("hour", Order.created_at), func.count())
            .where(Order.created_at >= since)
            .group_by(func.date_trunc("hour", Order.created_at))
        )
    ).all()
    peak_hourly = max((int(c) for _, c in hourly), default=0)

    # support SLA ≤2h (first staff reply)
    sla_rows = (
        await db.execute(
            select(
                SupportRequest.id,
                SupportRequest.created_at,
                func.min(SupportMessage.created_at),
            )
            .join(SupportMessage, SupportMessage.request_id == SupportRequest.id)
            .where(
                SupportRequest.created_at >= since,
                SupportMessage.is_staff.is_(True),
            )
            .group_by(SupportRequest.id, SupportRequest.created_at)
        )
    ).all()
    sla_secs = []
    for _, created, first_reply in sla_rows:
        if created and first_reply:
            sla_secs.append((first_reply - created).total_seconds())
    avg_support_sla = sum(sla_secs) / len(sla_secs) if sla_secs else None

    checks = [
        _threshold("generation_p95_sec_home_le_180", p95_gen, pass_if=bool(p95_home_ok)),
        _threshold("generation_p95_sec_cloud_le_300", p95_gen, pass_if=bool(p95_cloud_ok)),
        _threshold("success_rate_ge_95pct", round(success_rate, 4), pass_if=success_rate >= 0.95),
        _threshold("cancel_rate_le_5pct", round(cancel_rate, 4), pass_if=cancel_rate <= 0.05),
        _threshold("funnel_verify_ge_60pct", round(funnel_conv, 4), pass_if=funnel_conv >= 0.6),
        _threshold("rating_4_5_ge_80pct", round(rating_45_rate, 4), pass_if=rating_45_rate >= 0.8),
        _threshold("dwt_coverage_100pct", round(dwt_coverage, 4), pass_if=dwt_coverage >= 1.0),
        _threshold("nsfw_false_rate_lt_1pct", round(nsfw_false_rate, 4), pass_if=nsfw_false_rate < 0.01),
        _threshold("peak_orders_per_hour_ge_100", peak_hourly, pass_if=peak_hourly >= 100),
        _threshold("redlock_no_duplicate_processing", redlock_conflicts, pass_if=redlock_conflicts == 0),
        _threshold(
            "support_sla_avg_le_2h",
            round(avg_support_sla / 3600, 2) if avg_support_sla is not None else None,
            pass_if=avg_support_sla is not None and avg_support_sla <= 7200,
        ),
    ]

    passed = sum(1 for c in checks if c["pass"])
    return {
        "period_days": days,
        "since": since.isoformat(),
        "summary": {
            "passed": passed,
            "total": len(checks),
            "ready": passed >= 8,
        },
        "checks": checks,
        "raw": {
            "completed_orders": completed,
            "failed_orders": failed,
            "success_rate": round(success_rate, 4),
            "funnel_conversion": round(funnel_conv, 4),
            "p95_generation_sec": round(p95_gen, 1) if p95_gen is not None else None,
            "dwt_coverage": round(dwt_coverage, 4),
            "peak_orders_per_hour": peak_hourly,
            "redlock_conflicts": redlock_conflicts,
            "avg_support_sla_hours": round(avg_support_sla / 3600, 2) if avg_support_sla else None,
        },
        "note": "UNVERIFIED until run on staging/prod with real GPU workers",
    }
