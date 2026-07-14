"""Проверка SMART/диска/репликации MinIO → Telegram + email (§11.16.5 / §12.4)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlertLog
from app.services import alerts as alerts_svc
from app.services.minio import minio_service

logger = logging.getLogger(__name__)

COOLDOWN = timedelta(hours=1)
EVENT_DISK = "disk_fill"
EVENT_SMART = "disk_smart"
EVENT_REPL = "minio_replication"
EVENT_PG_LAG = "postgres_replication_lag"
EVENT_NODE = "storage_node_offline"
EVENT_TEMP = "storage_temp"
EVENT_SSD = "ssd_wear"


async def _recent_ok(db: AsyncSession, event_type: str, fingerprint: str) -> bool:
    since = datetime.now(timezone.utc) - COOLDOWN
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
        payload = r.payload or {}
        if payload.get("fingerprint") == fingerprint:
            return True
    return False


async def check_and_alert(db: AsyncSession) -> dict[str, Any]:
    """Celery / admin: disk / SMART / replication / PG lag / node (§11.16.5 dual-channel)."""
    from app.services import alert_thresholds as ath

    try:
        snap = minio_service.smart()
    except Exception as exc:  # noqa: BLE001
        logger.warning("storage smart check failed: %s", exc)
        return {"ok": False, "error": str(exc)[:300]}

    free_min = float(await ath.threshold_async("storage_disk_free_min_percent", 10))
    wear_min = float(await ath.threshold_async("storage_ssd_wear_min_percent", 15))
    temp_max = float(await ath.threshold_async("storage_temp_alert_c", 75))
    pg_lag_max = int(await ath.threshold_async("storage_pg_lag_alert_bytes", 1_073_741_824))
    repl_fail_min = float(await ath.threshold_async("storage_minio_repl_fail_minutes", 5))
    node_off_sec = float(await ath.threshold_async("storage_node_offline_seconds", 60))

    sent: list[str] = []
    used = snap.get("used_percent")
    free = snap.get("free_percent")
    status = (snap.get("smart") or {}).get("status") or "ok"
    disks = snap.get("smart_disks") or []
    ha = snap.get("cluster_ha") or {}

    # Свободное место < 10% (§11.16.5) или used ≥95%
    if snap.get("alert_disk_critical") or (free is not None and free < free_min) or (
        used is not None and used >= 95
    ):
        fp = f"disk_critical:{int(used or 0)}"
        if not await _recent_ok(db, EVENT_DISK, fp):
            text = (
                f"🚨 Диск MinIO critical\n"
                f"used: {used}%\n"
                f"free: {free}% (порог free <{free_min}%)\n"
                f"total_bytes: {snap.get('total_bytes')}\n"
                f"status: {status}"
            )
            dual = await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT_DISK,
                payload={"fingerprint": fp, "used_percent": used, "free_percent": free, "level": "critical"},
                subject="[3dvektor] Disk critical",
            )
            if dual.get("telegram") or dual.get("email"):
                sent.append("disk_critical")
    elif snap.get("alert_disk_high") or (used is not None and used >= 85):
        fp = f"disk_high:{int(used or 0) // 5 * 5}"
        if not await _recent_ok(db, EVENT_DISK, fp):
            text = (
                f"⚠️ Диск MinIO ≥85%\n"
                f"used: {used}%\n"
                f"free: {free}%\n"
                f"status: {status}"
            )
            dual = await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT_DISK,
                payload={"fingerprint": fp, "used_percent": used, "level": "warn"},
                subject="[3dvektor] Disk high ≥85%",
            )
            if dual.get("telegram") or dual.get("email"):
                sent.append("disk_high")

    bad_disks = []
    for d in disks:
        health = (d.get("health") or "").lower()
        realloc = int(d.get("reallocated_sectors") or 0)
        if health in ("fail", "failed", "critical", "warn", "warning") or realloc > 0:
            bad_disks.append(d)

    if bad_disks or status in ("smart_fail", "smart_warn"):
        names = ",".join(str(d.get("device") or d.get("model") or "?") for d in bad_disks[:5]) or status
        fp = f"smart:{status}:{names}"
        if not await _recent_ok(db, EVENT_SMART, fp):
            lines = [
                f"{'🚨' if status == 'smart_fail' else '⚠️'} SMART диск(и)\nstatus: {status}",
            ]
            for d in bad_disks[:8]:
                lines.append(
                    f"- {d.get('device') or d.get('model')}: health={d.get('health')} "
                    f"realloc={d.get('reallocated_sectors') or 0} temp={d.get('temp_c')}"
                )
            dual = await alerts_svc.send_dual(
                db,
                "\n".join(lines),
                event_type=EVENT_SMART,
                payload={"fingerprint": fp, "status": status, "disks": bad_disks[:8]},
                subject="[3dvektor] SMART disk alert",
            )
            if dual.get("telegram") or dual.get("email"):
                sent.append("smart")

    # Температура / износ SSD
    for d in disks:
        temp = d.get("temp_c")
        if temp is not None and float(temp) > temp_max:
            fp = f"temp:{d.get('device') or d.get('model')}:{int(float(temp))}"
            if not await _recent_ok(db, EVENT_TEMP, fp):
                dual = await alerts_svc.send_dual(
                    db,
                    f"⚠️ Температура диска >{temp_max}°C\n"
                    f"device: {d.get('device') or d.get('model')}\n"
                    f"temp_c: {temp}",
                    event_type=EVENT_TEMP,
                    payload={"fingerprint": fp, "temp_c": temp, "device": d.get("device")},
                    subject="[3dvektor] Storage temp alert",
                )
                if dual.get("telegram") or dual.get("email"):
                    sent.append("temp")
        wear = d.get("wear_percent")
        if wear is None:
            wear = d.get("remaining_life_percent")
        if wear is not None and float(wear) < wear_min:
            fp = f"ssd:{d.get('device')}:{int(float(wear))}"
            if not await _recent_ok(db, EVENT_SSD, fp):
                dual = await alerts_svc.send_dual(
                    db,
                    f"⚠️ Износ SSD <{wear_min}%\n"
                    f"device: {d.get('device') or d.get('model')}\n"
                    f"remaining: {wear}%",
                    event_type=EVENT_SSD,
                    payload={"fingerprint": fp, "wear_percent": wear},
                    subject="[3dvektor] SSD wear alert",
                )
                if dual.get("telegram") or dual.get("email"):
                    sent.append("ssd_wear")

    # MinIO replication Failed > N минут
    now = datetime.now(timezone.utc)
    for r in ha.get("minio_replication") or []:
        st = str(r.get("status") or "").lower()
        if st not in ("failed", "fail", "error"):
            continue
        failed_since = r.get("failed_since") or r.get("since")
        age_min = float(r.get("failed_minutes") or 0)
        if failed_since and not age_min:
            try:
                ts = datetime.fromisoformat(str(failed_since).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_min = (now - ts).total_seconds() / 60.0
            except Exception:  # noqa: BLE001
                age_min = repl_fail_min
        if age_min < repl_fail_min:
            continue
        bucket = r.get("bucket") or "?"
        fp = f"repl:{bucket}:{st}"
        if await _recent_ok(db, EVENT_REPL, fp):
            continue
        dual = await alerts_svc.send_dual(
            db,
            f"⚠️ MinIO replication {st} >{repl_fail_min:.0f} мин\n"
            f"bucket: {bucket}\n"
            f"pending: {r.get('pending') or r.get('pending_objects') or '—'}\n"
            f"failed_minutes: {age_min:.1f}",
            event_type=EVENT_REPL,
            payload={"fingerprint": fp, "bucket": bucket, "status": st, "age_min": age_min},
            subject=f"[3dvektor] MinIO replication {bucket}",
        )
        if dual.get("telegram") or dual.get("email"):
            sent.append(f"repl:{bucket}")

    # PG lag > 1 GiB
    pg = ha.get("postgres") or {}
    lag = pg.get("lag_bytes")
    if lag is not None and int(lag) > pg_lag_max:
        fp = f"pg_lag:{int(lag) // (1024 * 1024)}"
        if not await _recent_ok(db, EVENT_PG_LAG, fp):
            dual = await alerts_svc.send_dual(
                db,
                f"⚠️ PostgreSQL replication lag >1 GiB\n"
                f"lag_bytes: {lag}\n"
                f"role: {pg.get('role') or '—'}\n"
                f"wal_state: {pg.get('wal_state') or pg.get('state') or '—'}",
                event_type=EVENT_PG_LAG,
                payload={"fingerprint": fp, "lag_bytes": lag, "postgres": pg},
                subject="[3dvektor] PG replication lag",
            )
            if dual.get("telegram") or dual.get("email"):
                sent.append("pg_lag")

    # Узел offline > 60s (Tailscale heartbeat из HA JSON)
    for node in ha.get("nodes") or []:
        age = node.get("last_seen_age_sec")
        if age is None and node.get("last_seen"):
            try:
                ts = datetime.fromisoformat(str(node["last_seen"]).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age = (now - ts).total_seconds()
            except Exception:  # noqa: BLE001
                continue
        if age is None or float(age) < node_off_sec:
            continue
        nid = str(node.get("id") or node.get("name") or "?")
        fp = f"node:{nid}"
        if await _recent_ok(db, EVENT_NODE, fp):
            continue
        dual = await alerts_svc.send_dual(
            db,
            f"🚨 Узел хранения offline >{node_off_sec:.0f}s\n"
            f"node: {nid}\n"
            f"age_sec: {age}",
            event_type=EVENT_NODE,
            payload={"fingerprint": fp, "node": nid, "age_sec": age},
            subject=f"[3dvektor] Storage node offline {nid}",
        )
        if dual.get("telegram") or dual.get("email"):
            sent.append(f"node:{nid}")

    # Прогноз заполнения ≤30 дней (§23.7)
    try:
        from app.services import disk_forecast as df

        forecast = await df.disk_forecast(db, days_lookback=14)
        days_left = forecast.get("days_until_full")
        if days_left is not None and float(days_left) <= 30:
            fp = f"disk_forecast:{int(float(days_left))}"
            if not await _recent_ok(db, EVENT_DISK, fp):
                dual = await alerts_svc.send_dual(
                    db,
                    f"⚠️ Прогноз заполнения диска\n"
                    f"дней до 100%: {days_left}\n"
                    f"рост: {forecast.get('growth_percent_per_day')}%/день\n"
                    f"used: {forecast.get('current_used_percent')}%",
                    event_type=EVENT_DISK,
                    payload={
                        "fingerprint": fp,
                        "days_until_full": days_left,
                        "level": "forecast",
                    },
                    subject="[3dvektor] Disk fill forecast",
                )
                if dual.get("telegram") or dual.get("email"):
                    sent.append("disk_forecast")
        if forecast.get("wearout_alert"):
            for w in forecast.get("wearout") or []:
                if not (w.get("needs_replace") or w.get("bad_sectors")):
                    continue
                fp = f"wearout:{w.get('device')}:{w.get('wear_percent')}"
                if await _recent_ok(db, EVENT_SSD, fp):
                    continue
                dual = await alerts_svc.send_dual(
                    db,
                    f"⚠️ Диск требует замены\n"
                    f"device: {w.get('device')}\n"
                    f"wear: {w.get('wear_percent')}%\n"
                    f"realloc: {w.get('reallocated_sectors')}",
                    event_type=EVENT_SSD,
                    payload={"fingerprint": fp, **{k: w.get(k) for k in ("device", "wear_percent")}},
                    subject="[3dvektor] Disk wearout / sectors",
                )
                if dual.get("telegram") or dual.get("email"):
                    sent.append(f"wearout:{w.get('device')}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("disk forecast in storage_alerts: %s", exc)

    await db.commit()
    return {
        "ok": True,
        "status": status,
        "used_percent": used,
        "free_percent": free,
        "alerts_sent": sent,
        "disks": len(disks),
        "replication": len(ha.get("minio_replication") or []),
        "thresholds": {
            "free_min_percent": free_min,
            "ssd_wear_min": wear_min,
            "temp_max_c": temp_max,
            "pg_lag_bytes": pg_lag_max,
            "repl_fail_minutes": repl_fail_min,
            "node_offline_seconds": node_off_sec,
        },
    }
