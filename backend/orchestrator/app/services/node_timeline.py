"""История доступности узлов хранения §11.16.3 (Tailscale heartbeat)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StorageNodeEvent
from app.services.minio import minio_service

OFFLINE_SEC = 60


def _aware(dt: datetime | None, now: datetime) -> datetime:
    if dt is None:
        return now
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _node_status(node: dict[str, Any], *, offline_sec: float = OFFLINE_SEC) -> str:
    age = node.get("last_seen_age_sec")
    if age is None and node.get("last_seen"):
        try:
            ts = datetime.fromisoformat(str(node["last_seen"]).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
        except Exception:  # noqa: BLE001
            age = offline_sec + 1
    if age is None:
        # нет heartbeat — считаем online если явно status
        st = str(node.get("status") or "").lower()
        if st in ("offline", "down", "unreachable"):
            return "offline"
        return "online"
    return "offline" if float(age) > offline_sec else "online"


async def record_node_heartbeats(db: AsyncSession) -> dict[str, Any]:
    """Celery: сэмпл MINIO_HA nodes → open/close StorageNodeEvent."""
    now = datetime.now(timezone.utc)
    try:
        snap = minio_service.smart()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}
    ha = snap.get("cluster_ha") or {}
    nodes = ha.get("nodes") or []
    if not nodes:
        # synthetic from empty — no-op
        return {"ok": True, "nodes": 0, "transitions": 0}

    transitions = 0
    for node in nodes:
        nid = str(node.get("id") or node.get("name") or "unknown")
        name = str(node.get("name") or nid)
        status = _node_status(node)
        open_ev = await db.scalar(
            select(StorageNodeEvent)
            .where(StorageNodeEvent.node_id == nid, StorageNodeEvent.ended_at.is_(None))
            .order_by(StorageNodeEvent.id.desc())
            .limit(1)
        )
        if open_ev is None:
            db.add(
                StorageNodeEvent(
                    node_id=nid,
                    node_name=name,
                    status=status,
                    started_at=now,
                    meta={"source": "ha_json", "last_seen_age_sec": node.get("last_seen_age_sec")},
                )
            )
            transitions += 1
            continue
        if open_ev.status != status:
            open_ev.ended_at = now
            open_ev.duration_sec = int((now - _aware(open_ev.started_at, now)).total_seconds())
            db.add(
                StorageNodeEvent(
                    node_id=nid,
                    node_name=name,
                    status=status,
                    started_at=now,
                    meta={"source": "ha_json", "prev": open_ev.status},
                )
            )
            transitions += 1

    await db.commit()
    return {"ok": True, "nodes": len(nodes), "transitions": transitions}


async def node_timeline(db: AsyncSession, *, days: int = 7) -> dict[str, Any]:
    """Timeline offline/online сегментов для панели §11.16.3."""
    days = max(1, min(days, 90))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    rows = (
        await db.scalars(
            select(StorageNodeEvent)
            .where(StorageNodeEvent.started_at >= since - timedelta(days=1))
            .order_by(StorageNodeEvent.started_at.asc())
            .limit(2000)
        )
    ).all()

    by_node: dict[str, list[dict[str, Any]]] = {}
    offline_total: dict[str, float] = {}
    for ev in rows:
        end = _aware(ev.ended_at, now) if ev.ended_at else now
        start = _aware(ev.started_at, now)
        # clip to window
        if end < since:
            continue
        if start < since:
            start = since
        dur = max(0.0, (end - start).total_seconds())
        seg = {
            "id": ev.id,
            "status": ev.status,
            "started_at": start.isoformat(),
            "ended_at": end.isoformat() if ev.ended_at else None,
            "duration_sec": int(dur),
            "open": ev.ended_at is None,
        }
        by_node.setdefault(ev.node_id, []).append(seg)
        if ev.status == "offline":
            offline_total[ev.node_id] = offline_total.get(ev.node_id, 0.0) + dur

    nodes = []
    for nid, segs in by_node.items():
        name = next((r.node_name for r in rows if r.node_id == nid and r.node_name), nid)
        off = offline_total.get(nid, 0.0)
        window = days * 86400
        nodes.append(
            {
                "node_id": nid,
                "node_name": name,
                "segments": segs,
                "offline_sec": int(off),
                "offline_percent": round(100.0 * off / window, 2) if window else 0,
                "uptime_percent": round(100.0 * (1 - off / window), 2) if window else 100,
            }
        )
    nodes.sort(key=lambda n: n["node_id"])
    return {
        "days": days,
        "from": since.isoformat(),
        "to": now.isoformat(),
        "nodes": nodes,
        "as_of": now.isoformat(),
    }
