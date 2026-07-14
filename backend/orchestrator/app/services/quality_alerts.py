"""Алерты качества §12.4.1: конверсия публикации, fallback-сегментация."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AlertLog, SegmentationEvent
from app.services import alerts as alerts_svc
from app.services import publication_funnel as funnel_svc

logger = logging.getLogger(__name__)

EVENT_PUB_CONV = "publication_conversion"
EVENT_FALLBACK_SEG = "fallback_segmentation"


def _pub_threshold() -> float:
    return float(getattr(settings, "PUBLICATION_CONVERSION_ALERT_RATIO", 0.30) or 0.30)


def _seg_threshold() -> float:
    return float(getattr(settings, "FALLBACK_SEGMENTATION_ALERT_RATIO", 0.15) or 0.15)


def _seg_min_samples() -> int:
    return int(getattr(settings, "FALLBACK_SEGMENTATION_MIN_SAMPLES", 10) or 10)


async def _recent_ok(db: AsyncSession, event_type: str, fingerprint: str, *, hours: float = 24) -> bool:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        await db.scalars(
            select(AlertLog)
            .where(
                AlertLog.event_type == event_type,
                AlertLog.ok.is_(True),
                AlertLog.created_at >= since,
            )
            .order_by(AlertLog.id.desc())
            .limit(40)
        )
    ).all()
    for r in rows:
        if (r.payload or {}).get("fingerprint") == fingerprint:
            return True
    return False


async def check_publication_conversion(db: AsyncSession) -> dict[str, Any]:
    """Отметок от скачиваний <30% за неделю → Email (§12.4.1)."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    payload = await funnel_svc.global_funnel(db, date_from=since, date_to=None)
    funnel = payload.get("funnel") or {}
    conv = funnel.get("conversion") or {}
    downloaded = int(funnel.get("downloaded") or 0)
    verified = int(funnel.get("verified") or 0)
    ratio = float(conv.get("downloaded_to_verified") or 0)
    if downloaded == 0:
        ratio = 0.0
    thr = _pub_threshold()
    try:
        from app.services import alert_thresholds as ath

        thr = float(await ath.threshold_async("publication_conversion_alert_ratio", thr))
    except Exception:  # noqa: BLE001
        pass
    sent = False
    if downloaded >= 5 and ratio < thr:
        fp = f"pub_conv:{since.date().isoformat()}"
        if not await _recent_ok(db, EVENT_PUB_CONV, fp, hours=24 * 6):
            text = (
                f"📉 Конверсия публикации <{thr * 100:.0f}% за неделю\n"
                f"downloaded: {downloaded}\n"
                f"verified: {verified}\n"
                f"ratio: {ratio:.2%}"
            )
            dual = await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT_PUB_CONV,
                payload={
                    "fingerprint": fp,
                    "downloaded": downloaded,
                    "verified": verified,
                    "ratio": ratio,
                    "threshold": thr,
                },
                subject="[3dvektor] Publication conversion low",
                telegram=False,
                email=True,
            )
            sent = bool(dual.get("email"))
    return {
        "ok": True,
        "downloaded": downloaded,
        "verified": verified,
        "ratio": ratio,
        "threshold": thr,
        "alert_sent": sent,
    }


async def check_fallback_segmentation(db: AsyncSession) -> dict[str, Any]:
    """Доля failed/fallback сегментации по устройству >15% за 24ч → Email (§11.2.5 / §12.4.1)."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = (
        await db.scalars(select(SegmentationEvent).where(SegmentationEvent.created_at >= since))
    ).all()
    thr = _seg_threshold()
    try:
        from app.services import alert_thresholds as ath

        thr = float(await ath.threshold_async("fallback_segmentation_alert_ratio", thr))
    except Exception:  # noqa: BLE001
        pass
    min_n = _seg_min_samples()
    buckets: dict[str, dict[str, int]] = {}
    for r in rows:
        key = f"{r.device_model or 'unknown'}|{r.os_version or 'unknown'}"
        b = buckets.setdefault(key, {"total": 0, "failed": 0, "fallback": 0})
        b["total"] += 1
        if r.failed:
            b["failed"] += 1
        if r.fallback_used:
            b["fallback"] += 1

    alerts: list[dict[str, Any]] = []
    for key, b in buckets.items():
        if b["total"] < min_n:
            continue
        fail_rate = b["failed"] / b["total"]
        fb_rate = b["fallback"] / b["total"]
        # ТЗ: неудачные сегментации ИЛИ высокий fallback (SAM) по устройству
        rate = max(fail_rate, fb_rate)
        if rate < thr:
            continue
        device, os_ver = (key.split("|", 1) + ["unknown"])[:2]
        fp = f"seg:{key}:{since.date().isoformat()}"
        if await _recent_ok(db, EVENT_FALLBACK_SEG, fp, hours=20):
            continue
        text = (
            f"⚠️ Fallback/failed сегментация >{thr * 100:.0f}% / 24ч\n"
            f"device: {device}\n"
            f"os: {os_ver}\n"
            f"total: {b['total']}\n"
            f"failed: {b['failed']} ({fail_rate:.1%})\n"
            f"fallback_sam: {b['fallback']} ({fb_rate:.1%})"
        )
        dual = await alerts_svc.send_dual(
            db,
            text,
            event_type=EVENT_FALLBACK_SEG,
            payload={
                "fingerprint": fp,
                "device_model": device,
                "os_version": os_ver,
                "total": b["total"],
                "failed_rate": fail_rate,
                "fallback_rate": fb_rate,
                "threshold": thr,
            },
            subject=f"[3dvektor] Segmentation alert {device}",
            telegram=False,
            email=True,
        )
        if dual.get("email"):
            alerts.append({"device": device, "os": os_ver, "rate": rate})

    await db.commit()
    return {"ok": True, "devices_checked": len(buckets), "alerts_sent": alerts, "threshold": thr}


async def record_segmentation(
    db: AsyncSession,
    *,
    task_id: str,
    device_model: str | None,
    os_version: str | None,
    fallback_used: bool,
    failed: bool,
    avg_confidence: float | None = None,
    method: str | None = None,
) -> None:
    db.add(
        SegmentationEvent(
            task_id=task_id,
            device_model=(device_model or "unknown")[:64],
            os_version=(os_version or "unknown")[:64],
            fallback_used=fallback_used,
            failed=failed,
            avg_confidence=avg_confidence,
            method=(method or "")[:32] or None,
        )
    )
    await db.flush()


async def ingest_from_worker_event(
    db: AsyncSession,
    *,
    task_id: str,
    data: dict[str, Any] | None = None,
    failed: bool | None = None,
) -> None:
    """Записать SegmentationEvent из WS/HTTP события воркера."""
    from app.models import TaskQueue

    data = data or {}
    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    payload = dict(row.payload_json or {}) if row else {}
    seg = data.get("segmentation") if isinstance(data.get("segmentation"), dict) else {}
    frames = seg.get("frames") or []
    methods = [str(f.get("method") or "") for f in frames if isinstance(f, dict)]
    fallback = bool(seg.get("fallback_used")) or any(m == "sam" for m in methods)
    method = None
    if methods:
        # доминирующий метод
        method = max(set(methods), key=methods.count)
    is_failed = bool(failed) if failed is not None else bool(seg.get("failed"))
    if data.get("error") and "failed_segmentation" in str(data.get("error")):
        is_failed = True
        fallback = True
    avg = seg.get("avg_confidence")
    try:
        avg_f = float(avg) if avg is not None else None
    except (TypeError, ValueError):
        avg_f = None
    await record_segmentation(
        db,
        task_id=task_id,
        device_model=str(data.get("device_model") or payload.get("device_model") or "unknown"),
        os_version=str(data.get("os_version") or payload.get("os_version") or "unknown"),
        fallback_used=fallback,
        failed=is_failed,
        avg_confidence=avg_f,
        method=method,
    )


async def check_and_alert(db: AsyncSession) -> dict[str, Any]:
    pub = await check_publication_conversion(db)
    seg = await check_fallback_segmentation(db)
    return {"publication": pub, "segmentation": seg}
