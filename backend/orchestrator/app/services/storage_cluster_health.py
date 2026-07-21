"""Storage cluster health — 2-node cards §23.4."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.minio import minio_service

_NODE_IDS = ("node-a", "node-b")


def _node_status(*, online: bool, disk_critical: bool, repl_failed: bool, age_sec: int | None) -> str:
    if not online:
        return "offline"
    if disk_critical or repl_failed:
        return "degraded"
    if age_sec is not None and age_sec > 300:
        return "stale"
    return "healthy"


def storage_cluster_health() -> dict[str, Any]:
    smart = minio_service.smart()
    ha = smart.get("cluster_ha") or {}
    raw_nodes = ha.get("nodes") or []
    disks = smart.get("smart_disks") or []
    repl = ha.get("minio_replication") or []
    pg = ha.get("postgres") or {}
    disk_critical = bool(smart.get("alert_disk_critical"))
    repl_failed = bool(smart.get("alert_replication_failed"))

    cards: list[dict[str, Any]] = []
    for idx, node_id in enumerate(_NODE_IDS):
        src = raw_nodes[idx] if idx < len(raw_nodes) else {}
        disk = disks[idx] if idx < len(disks) else {}
        age = src.get("last_seen_age_sec")
        if age is None and src.get("last_seen"):
            try:
                seen = datetime.fromisoformat(str(src["last_seen"]).replace("Z", "+00:00"))
                age = int((datetime.now(timezone.utc) - seen).total_seconds())
            except Exception:  # noqa: BLE001
                age = None
        online = bool(smart.get("ok")) and (age is None or age < 600)
        cards.append(
            {
                "node_id": src.get("id") or src.get("name") or node_id,
                "hostname": src.get("name") or f"minio-{idx + 1}",
                "status": _node_status(
                    online=online,
                    disk_critical=disk_critical,
                    repl_failed=repl_failed,
                    age_sec=int(age) if age is not None else None,
                ),
                "last_seen": src.get("last_seen"),
                "last_seen_age_sec": age,
                "disk": {
                    "device": disk.get("device") or disk.get("model"),
                    "health": disk.get("health"),
                    "used_percent": disk.get("used_percent") or smart.get("used_percent"),
                    "temp_c": disk.get("temp_c"),
                    "wear_percent": disk.get("wear_percent") or disk.get("remaining_life_percent"),
                },
                "minio_replication": [
                    r for r in repl if str(r.get("node") or "").lower() in (node_id, f"minio-{idx + 1}", "")
                ]
                or (repl[idx : idx + 1] if idx < len(repl) else []),
            }
        )

    overall = "healthy"
    if any(c["status"] == "offline" for c in cards):
        overall = "offline"
    elif any(c["status"] in ("degraded", "stale") for c in cards):
        overall = "degraded"

    return {
        "overall": overall,
        "nodes": cards,
        "postgres": pg,
        "alert_replication_failed": repl_failed,
        "alert_disk_critical": disk_critical,
        "used_percent": smart.get("used_percent"),
        "source": ha.get("source"),
    }
