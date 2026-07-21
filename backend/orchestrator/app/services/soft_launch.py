"""Soft-launch KPI + checklist persistence (§11 / воронка / конверсия ≥60%)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Model3D, Order, SoftLaunchChecklist, Transaction
from app.services import publication_funnel as funnel_svc

CHECKLIST_ITEMS: list[dict[str, str]] = [
    {"id": "env", "section": "Секреты", "label": "Prod secrets / PD_ENCRYPTION / Vault"},
    {"id": "yookassa", "section": "Секреты", "label": "ЮKassa + webhook"},
    {"id": "vpn2fa", "section": "Секреты", "label": "Admin VPN + 2FA"},
    {"id": "alembic", "section": "Инфра", "label": "Alembic upgrade head"},
    {"id": "minio", "section": "Инфра", "label": "MinIO buckets + lifecycle"},
    {"id": "backup", "section": "Инфра", "label": "PG backup → MinIO"},
    {"id": "gpu_e2e", "section": "GPU", "label": "TRELLIS.2 E2E exit 0 (без stub)"},
    {"id": "burn", "section": "GPU", "label": "Cloud burn ₽/ч в лимите"},
    {"id": "tax", "section": "Платежи", "label": "Налоговый режим владельца"},
    {"id": "payment", "section": "Платежи", "label": "Тестовый платёж + чек"},
    {"id": "funnel", "section": "Продукт", "label": "Заказ → gen → download → verify"},
    {"id": "b2b", "section": "Продукт", "label": "B2B invite / roles / webhooks"},
    {"id": "support", "section": "Support", "label": "FAQ + ticket create/reply"},
    {"id": "nsfw", "section": "Support", "label": "NSFW queue + refund"},
    {"id": "mobile", "section": "Mobile", "label": "Guided Dome + thermal + push"},
    {"id": "alerts", "section": "Gate", "label": "Telegram alerts + rollback plan"},
]

VALID_CHECK_IDS = {i["id"] for i in CHECKLIST_ITEMS}
SINGLETON_ID = 1


async def soft_launch_kpi(db: AsyncSession, *, days: int = 7) -> dict[str, Any]:
    """Живые KPI для soft launch dashboard."""
    days = max(1, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    funnel_payload = await funnel_svc.global_funnel(db, date_from=since, date_to=None)
    funnel = funnel_payload.get("funnel") or {}
    conv = funnel.get("conversion") or {}

    by_status_rows = (
        await db.execute(
            select(Order.status, func.count())
            .where(Order.created_at >= since)
            .group_by(Order.status)
        )
    ).all()
    by_status = {str(s): int(c) for s, c in by_status_rows}
    total_orders = sum(by_status.values())
    cancelled = int(by_status.get("cancelled", 0) + by_status.get("cancelled_by_user_no_refund", 0))
    completed = int(by_status.get("completed", 0))
    nsfw = int(by_status.get("blocked_nsfw", 0) + by_status.get("nsfw_blocked", 0))

    paid = int(
        await db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.created_at >= since,
                Order.status.in_(("paid", "queued", "processing", "completed")),
            )
        )
        or 0
    )

    revenue = int(
        await db.scalar(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.created_at >= since,
                Order.status.in_(("completed", "paid", "queued", "processing")),
            )
        )
        or 0
    )
    refunds = int(
        await db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.created_at >= since,
                Transaction.tx_type.in_(("refund", "refund_card", "refund_balance")),
            )
        )
        or 0
    )

    models_n = int(
        await db.scalar(select(func.count()).select_from(Model3D).where(Model3D.created_at >= since))
        or 0
    )

    # целевая конверсия ТЗ: оплата → gen → download → verify ≥ 60%
    pay_to_verify = float(conv.get("generated_to_verified") or conv.get("download_to_verified") or 0)
    gen_to_dl = float(conv.get("generated_to_downloaded") or 0)
    target_ok = pay_to_verify >= 0.6 or (
        float(funnel.get("verified") or 0) / max(float(funnel.get("generated") or 0), 1) >= 0.6
    )

    day_bucket = func.date_trunc("day", Order.created_at).label("day_bucket")
    daily = (
        await db.execute(
            select(day_bucket, func.count())
            .where(Order.created_at >= since)
            .group_by(day_bucket)
            .order_by(day_bucket)
        )
    ).all()

    return {
        "period_days": days,
        "since": since.isoformat(),
        "funnel": {
            "generated": funnel.get("generated", 0),
            "downloaded": funnel.get("downloaded", 0),
            "links_added": funnel.get("links_added", 0),
            "verified": funnel.get("verified", 0),
            "manual_marked": funnel.get("manual_marked", 0),
            "conversion": conv,
        },
        "orders": {
            "total": total_orders,
            "paid_pipeline": paid,
            "completed": completed,
            "cancelled": cancelled,
            "nsfw_blocked": nsfw,
            "cancel_rate": round(cancelled / max(total_orders, 1), 4),
            "by_status": by_status,
        },
        "finance": {"revenue_rub": revenue, "refunds_rub": abs(refunds)},
        "models_created": models_n,
        "kpi": {
            "funnel_conversion": round(
                float(funnel.get("verified") or 0) / max(float(funnel.get("generated") or 1), 1),
                4,
            ),
            "gen_to_download": round(gen_to_dl, 4),
            "target_conversion_60": target_ok,
            "cancel_rate_ok": (cancelled / max(total_orders, 1)) <= 0.05,
        },
        "orders_daily": [
            {"day": (r[0].date().isoformat() if r[0] else None), "count": int(r[1])} for r in daily
        ],
    }


def kpi_to_csv(data: dict[str, Any]) -> str:
    """CSV soft-launch KPI: summary + daily + by_status."""
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["section", "metric", "value"])
    w.writerow(["meta", "period_days", data.get("period_days")])
    w.writerow(["meta", "since", data.get("since")])
    funnel = data.get("funnel") or {}
    for k in ("generated", "downloaded", "links_added", "verified", "manual_marked"):
        w.writerow(["funnel", k, funnel.get(k, 0)])
    conv = funnel.get("conversion") or {}
    for k, v in conv.items():
        w.writerow(["funnel_conversion", k, v])
    orders = data.get("orders") or {}
    for k in ("total", "paid_pipeline", "completed", "cancelled", "nsfw_blocked", "cancel_rate"):
        w.writerow(["orders", k, orders.get(k)])
    for st, cnt in (orders.get("by_status") or {}).items():
        w.writerow(["orders_by_status", st, cnt])
    finance = data.get("finance") or {}
    for k, v in finance.items():
        w.writerow(["finance", k, v])
    w.writerow(["models", "created", data.get("models_created")])
    kpi = data.get("kpi") or {}
    for k, v in kpi.items():
        w.writerow(["kpi", k, v])
    w.writerow([])
    w.writerow(["day", "orders_count"])
    for row in data.get("orders_daily") or []:
        w.writerow([row.get("day"), row.get("count")])
    return buf.getvalue()


def normalize_checks(raw: dict | None) -> dict[str, bool]:
    out = {i["id"]: False for i in CHECKLIST_ITEMS}
    if not raw:
        return out
    for k, v in raw.items():
        if k in VALID_CHECK_IDS:
            out[k] = bool(v)
    return out


async def get_checklist(db: AsyncSession) -> dict[str, Any]:
    row = await db.get(SoftLaunchChecklist, SINGLETON_ID)
    checks = normalize_checks(row.checks if row else {})
    done = sum(1 for v in checks.values() if v)
    return {
        "items": CHECKLIST_ITEMS,
        "checks": checks,
        "done": done,
        "total": len(CHECKLIST_ITEMS),
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
        "updated_by_user_id": row.updated_by_user_id if row else None,
    }


async def put_checklist(
    db: AsyncSession,
    *,
    checks: dict[str, bool],
    user_id: int | None = None,
) -> dict[str, Any]:
    normalized = normalize_checks(checks)
    row = await db.get(SoftLaunchChecklist, SINGLETON_ID)
    if not row:
        row = SoftLaunchChecklist(id=SINGLETON_ID, checks=normalized, updated_by_user_id=user_id)
        db.add(row)
    else:
        row.checks = normalized
        row.updated_by_user_id = user_id
        row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return await get_checklist(db)
