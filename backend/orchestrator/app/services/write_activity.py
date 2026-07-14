"""Write Activity Heartbeat §11.16.5 / §23.4: нет записи >10 мин при нагрузке."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlertLog, Order, TaskQueue, Transaction
from app.services import alerts as alerts_svc
from app.services.minio import minio_service

logger = logging.getLogger(__name__)

EVENT = "write_activity_stale"
COOLDOWN = timedelta(hours=1)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _recent_ok(db: AsyncSession, fingerprint: str) -> bool:
    since = datetime.now(timezone.utc) - COOLDOWN
    rows = (
        await db.scalars(
            select(AlertLog)
            .where(
                AlertLog.event_type == EVENT,
                AlertLog.ok.is_(True),
                AlertLog.created_at >= since,
            )
            .order_by(AlertLog.id.desc())
            .limit(20)
        )
    ).all()
    return any((r.payload or {}).get("fingerprint") == fingerprint for r in rows)


async def snapshot_write_activity(db: AsyncSession) -> dict[str, Any]:
    """TPS-подобные метрики + last write timestamps."""
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)

    tx_1h = int(
        await db.scalar(
            select(func.count()).select_from(Transaction).where(Transaction.created_at >= hour_ago)
        )
        or 0
    )
    orders_1h = int(
        await db.scalar(select(func.count()).select_from(Order).where(Order.created_at >= hour_ago))
        or 0
    )
    last_tx = await db.scalar(select(func.max(Transaction.created_at)))
    last_order = await db.scalar(select(func.max(Order.created_at)))
    last_task = await db.scalar(select(func.max(TaskQueue.updated_at)))

    queued = int(
        await db.scalar(
            select(func.count())
            .select_from(TaskQueue)
            .where(TaskQueue.status.in_(("queued", "pending", "processing")))
        )
        or 0
    )
    processing = int(
        await db.scalar(
            select(func.count()).select_from(TaskQueue).where(TaskQueue.status == "processing")
        )
        or 0
    )

    # MinIO last write из HA/SMART sidecar
    ha = {}
    try:
        snap = minio_service.smart()
        ha = snap.get("cluster_ha") or {}
    except Exception:  # noqa: BLE001
        snap = {}
    minio_last = ha.get("minio_last_write") or ha.get("last_write") or (ha.get("write_activity") or {}).get(
        "minio_last_write"
    )
    minio_objects_1h = (ha.get("write_activity") or {}).get("minio_objects_1h")

    candidates = [_aware(last_tx), _aware(last_order), _aware(last_task)]
    if minio_last:
        try:
            candidates.append(_aware(datetime.fromisoformat(str(minio_last).replace("Z", "+00:00"))))
        except Exception:  # noqa: BLE001
            pass
    candidates = [c for c in candidates if c]
    last_write = max(candidates) if candidates else None
    stale_sec = (now - last_write).total_seconds() if last_write else None
    under_load = queued > 0 or processing > 0

    return {
        "now": now.isoformat(),
        "under_load": under_load,
        "freeze_indicator": under_load and stale_sec is not None and stale_sec >= 5 * 60,
        "queued_tasks": queued,
        "processing_tasks": processing,
        "pg_tx_1h": tx_1h,
        "orders_1h": orders_1h,
        "minio_objects_1h": minio_objects_1h,
        "last_write_at": last_write.isoformat() if last_write else None,
        "stale_seconds": round(stale_sec, 1) if stale_sec is not None else None,
        "sources": {
            "last_transaction": last_tx.isoformat() if last_tx else None,
            "last_order": last_order.isoformat() if last_order else None,
            "last_task_queue": last_task.isoformat() if last_task else None,
            "minio_last_write": minio_last,
        },
    }


async def check_and_alert(db: AsyncSession) -> dict[str, Any]:
    """
    Отсутствие записи в БД/MinIO >10 мин при нагрузке → Critical dual-channel (§11.16.5).
    UI-индикатор «заморозки» при >5 мин (возвращается в snapshot).
    """
    from app.services import alert_thresholds as ath

    snap = await snapshot_write_activity(db)
    thr_min = float(await ath.threshold_async("storage_write_stale_minutes", 10))
    warn_min = float(await ath.threshold_async("storage_write_freeze_minutes", 5))
    stale_sec = snap.get("stale_seconds")
    under_load = bool(snap.get("under_load"))
    freeze = under_load and stale_sec is not None and stale_sec >= warn_min * 60
    critical = under_load and stale_sec is not None and stale_sec >= thr_min * 60

    sent = False
    if critical:
        fp = f"write_stale:{int(stale_sec // 60)}"
        if not await _recent_ok(db, fp):
            text = (
                f"🚨 Нет записи данных >{thr_min:.0f} мин при нагрузке\n"
                f"stale_sec: {stale_sec:.0f}\n"
                f"queued: {snap.get('queued_tasks')}\n"
                f"processing: {snap.get('processing_tasks')}\n"
                f"last_write: {snap.get('last_write_at')}\n"
                f"pg_tx_1h: {snap.get('pg_tx_1h')}"
            )
            dual = await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT,
                payload={
                    "fingerprint": fp,
                    **{k: snap[k] for k in ("queued_tasks", "processing_tasks", "stale_seconds", "last_write_at")},
                },
                subject="[3dvektor] Write activity stale",
            )
            sent = bool(dual.get("telegram") or dual.get("email"))
            await db.commit()

    return {
        "ok": True,
        "freeze_indicator": freeze,
        "critical": critical,
        "alert_sent": sent,
        "threshold_minutes": thr_min,
        "freeze_minutes": warn_min,
        **snap,
    }
