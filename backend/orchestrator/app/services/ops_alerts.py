"""Операционные алерты §12.4.1: очередь, all-busy, worker offline."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AlertLog, WorkerNode
from app.services import alerts as alerts_svc
from app.services.queue import queue_service
from app.services.worker_hub import worker_hub

logger = logging.getLogger(__name__)

EVENT_QUEUE = "queue_length"
EVENT_ALL_BUSY = "all_workers_busy"
EVENT_OFFLINE = "worker_offline"

# all-busy: monotonic timestamp when first detected
_all_busy_since: float | None = None


def _queue_threshold() -> int:
    return int(getattr(settings, "QUEUE_ALERT_LENGTH", 20) or 20)


def _all_busy_minutes() -> float:
    return float(getattr(settings, "ALL_BUSY_ALERT_MINUTES", 5) or 5)


def _offline_seconds() -> float:
    return float(getattr(settings, "WORKER_OFFLINE_ALERT_SECONDS", 30) or 30)


def _cooldown_sec(event: str) -> float:
    if event == EVENT_OFFLINE:
        return float(getattr(settings, "WORKER_OFFLINE_ALERT_COOLDOWN_SEC", 600) or 600)
    if event == EVENT_QUEUE:
        return float(getattr(settings, "QUEUE_ALERT_COOLDOWN_SEC", 900) or 900)
    return float(getattr(settings, "ALL_BUSY_ALERT_COOLDOWN_SEC", 900) or 900)


async def _recent_ok(db: AsyncSession, event_type: str, fingerprint: str, *, cooldown: float) -> bool:
    since = datetime.now(timezone.utc) - timedelta(seconds=cooldown)
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


async def check_and_alert(db: AsyncSession) -> dict[str, Any]:
    """Celery: пороги §12.4.1 → Telegram + email."""
    global _all_busy_since
    from app.services import alert_thresholds as ath

    sent: list[str] = []
    lengths = {"normal": 0, "high": 0}
    try:
        lengths = await queue_service.queue_lengths()
    except Exception as exc:  # noqa: BLE001
        logger.warning("queue lengths failed: %s", exc)

    q_thr = int(await ath.threshold_async("queue_alert_length", _queue_threshold()))
    busy_min = float(await ath.threshold_async("all_busy_alert_minutes", _all_busy_minutes()))
    offline_thr = float(
        await ath.threshold_async("worker_offline_alert_seconds", _offline_seconds())
    )

    total_q = int(lengths.get("normal") or 0) + int(lengths.get("high") or 0)
    if total_q > q_thr:
        fp = f"queue:{total_q // 5 * 5}"
        if not await _recent_ok(db, EVENT_QUEUE, fp, cooldown=_cooldown_sec(EVENT_QUEUE)):
            text = (
                f"⚠️ Длина очереди >{q_thr}\n"
                f"total: {total_q}\n"
                f"normal: {lengths.get('normal')}\n"
                f"high: {lengths.get('high')}"
            )
            dual = await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT_QUEUE,
                payload={"fingerprint": fp, "total": total_q, "lengths": lengths},
                subject=f"[3dvektor] Queue length {total_q}",
            )
            if dual.get("telegram") or dual.get("email"):
                sent.append("queue_length")
            try:
                from app.models import AutoscalingRule
                from app.services import cloud_autoscaling as cas

                rule_row = (
                    await db.scalars(
                        select(AutoscalingRule)
                        .where(AutoscalingRule.is_active.is_(True), AutoscalingRule.auto_launch.is_(False))
                        .limit(1)
                    )
                ).first()
                if rule_row:
                    await cas.mark_scale_pending(queue=total_q, rule_id=rule_row.id, reason="queue_alert")
            except Exception as exc:  # noqa: BLE001
                logger.debug("scale pending on queue alert: %s", exc)

    # all workers busy > N minutes
    snap = await worker_hub.list_snapshot()
    live = [w for w in snap if w.get("status") not in ("offline",)]
    busy_like = [w for w in live if w.get("status") in ("busy", "overheated")]
    all_busy = bool(live) and len(busy_like) == len(live) and len(live) > 0
    now_m = time.monotonic()
    if all_busy:
        if _all_busy_since is None:
            _all_busy_since = now_m
        elapsed_min = (now_m - _all_busy_since) / 60.0
        if elapsed_min >= busy_min:
            fp = f"all_busy:{len(live)}"
            if not await _recent_ok(db, EVENT_ALL_BUSY, fp, cooldown=_cooldown_sec(EVENT_ALL_BUSY)):
                text = (
                    f"🚨 Все воркеры busy >{busy_min:.0f} мин\n"
                    f"workers: {len(live)}\n"
                    f"elapsed_min: {elapsed_min:.1f}"
                )
                dual = await alerts_svc.send_dual(
                    db,
                    text,
                    event_type=EVENT_ALL_BUSY,
                    payload={
                        "fingerprint": fp,
                        "workers": len(live),
                        "elapsed_min": round(elapsed_min, 2),
                    },
                    subject="[3dvektor] All workers busy",
                )
                if dual.get("telegram") or dual.get("email"):
                    sent.append("all_workers_busy")
    else:
        _all_busy_since = None

    # worker offline: no heartbeat > threshold (hub + PG)
    now = datetime.now(timezone.utc)
    hub_ids = {w["worker_id"] for w in snap}
    for w in snap:
        hb = w.get("last_heartbeat")
        try:
            ts = datetime.fromisoformat(hb) if isinstance(hb, str) else now
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            continue
        age = (now - ts).total_seconds()
        if age < offline_thr:
            continue
        wid = str(w["worker_id"])
        fp = f"offline:{wid}"
        if await _recent_ok(db, EVENT_OFFLINE, fp, cooldown=_cooldown_sec(EVENT_OFFLINE)):
            continue
        text = (
            f"⚠️ Воркер offline\n"
            f"worker_id: {wid}\n"
            f"no heartbeat: {age:.0f}s (порог {offline_thr:.0f}s)\n"
            f"last_status: {w.get('status')}"
        )
        dual = await alerts_svc.send_dual(
            db,
            text,
            event_type=EVENT_OFFLINE,
            payload={"fingerprint": fp, "worker_id": wid, "age_sec": age},
            subject=f"[3dvektor] Worker offline {wid}",
            # ТЗ: Telegram + email
        )
        if dual.get("telegram") or dual.get("email"):
            sent.append(f"offline:{wid}")

    # PG nodes marked online but stale (не в hub)
    rows = (await db.scalars(select(WorkerNode).where(WorkerNode.status != "offline"))).all()
    for node in rows:
        if node.id in hub_ids:
            continue
        hb = node.last_heartbeat
        if not hb:
            continue
        if hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)
        age = (now - hb).total_seconds()
        if age < offline_thr:
            continue
        fp = f"offline_pg:{node.id}"
        if await _recent_ok(db, EVENT_OFFLINE, fp, cooldown=_cooldown_sec(EVENT_OFFLINE)):
            continue
        text = (
            f"⚠️ Воркер offline (PG)\n"
            f"worker_id: {node.id}\n"
            f"no heartbeat: {age:.0f}s\n"
            f"db_status: {node.status}"
        )
        dual = await alerts_svc.send_dual(
            db,
            text,
            event_type=EVENT_OFFLINE,
            payload={"fingerprint": fp, "worker_id": node.id, "age_sec": age, "source": "pg"},
            subject=f"[3dvektor] Worker offline {node.id}",
        )
        if dual.get("telegram") or dual.get("email"):
            sent.append(f"offline_pg:{node.id}")
            node.status = "offline"

    await db.commit()
    return {
        "ok": True,
        "queue_total": total_q,
        "queue_threshold": q_thr,
        "all_busy": all_busy,
        "live_workers": len(live),
        "alerts_sent": sent,
    }
