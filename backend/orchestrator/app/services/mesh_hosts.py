"""Tailscale mesh / multi-host storage fallback §4.3 / §22."""

from __future__ import annotations

import socket
from typing import Any

from app.core.config import settings


def _parse_hosts(raw: str) -> list[str]:
    return [h.strip() for h in (raw or "").split(",") if h.strip()]


def _tcp_ping(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def mesh_storage_hosts() -> dict[str, list[str]]:
    return {
        "postgres": _parse_hosts(settings.MESH_POSTGRES_HOSTS),
        "redis": _parse_hosts(settings.MESH_REDIS_HOSTS),
        "minio": _parse_hosts(settings.MESH_MINIO_HOSTS),
    }


def mesh_status() -> dict[str, Any]:
    """Проверка доступности узлов mesh (Tailscale IP)."""
    hosts = mesh_storage_hosts()
    checks: dict[str, Any] = {}
    for role, items in hosts.items():
        port = {"postgres": 5432, "redis": 6379, "minio": 9000}.get(role, 0)
        role_checks = []
        for host in items:
            ok = _tcp_ping(host, port) if port else False
            role_checks.append({"host": host, "port": port, "ok": ok})
        checks[role] = role_checks
    any_configured = any(hosts.values())
    online = sum(1 for rows in checks.values() for r in rows if r.get("ok"))
    total = sum(len(rows) for rows in checks.values())
    return {
        "configured": any_configured,
        "hosts": hosts,
        "checks": checks,
        "online": online,
        "total": total,
        "ok": not any_configured or online > 0,
        "primary": {
            "postgres": settings.POSTGRES_HOST,
            "redis": settings.REDIS_URL,
            "minio": settings.MINIO_ENDPOINT,
        },
        "ws_fallback": (settings.ORCHESTRATOR_WS_FALLBACK_URL or "").strip() or None,
    }


def mesh_recommendations() -> list[str]:
    rec: list[str] = []
    st = mesh_status()
    if not st["configured"]:
        rec.append("Set MESH_*_HOSTS with Tailscale IPs for application-level failover")
        return rec
    for role, rows in st["checks"].items():
        alive = [r["host"] for r in rows if r.get("ok")]
        if not alive:
            rec.append(f"No online {role} mesh nodes")
        elif len(alive) < len(rows):
            rec.append(f"{role}: partial mesh ({len(alive)}/{len(rows)} online)")
    return rec
