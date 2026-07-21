"""§9.6 MinIO VIP / Keepalived health."""

from __future__ import annotations

import socket
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings


def _host_port(endpoint: str) -> tuple[str, int]:
    raw = (endpoint or "").strip()
    if not raw:
        return "", 0
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if parsed.scheme in ("http", "https") and parsed.port is None and parsed.scheme == "http":
        port = 9000 if "minio" in host or host.startswith("100.") else 80
    return host, port


def minio_vip_status() -> dict[str, Any]:
    vip = (settings.MINIO_VIP or "").strip()
    primary = (settings.MINIO_ENDPOINT or "").strip()
    out: dict[str, Any] = {
        "vip": vip or None,
        "primary_endpoint": primary,
        "replica_endpoint": (settings.MINIO_REPLICA_ENDPOINT or "").strip() or None,
        "configured": bool(vip),
        "ok": False,
    }
    if not vip:
        out["note"] = "MINIO_VIP not set — using MINIO_ENDPOINT only"
        host, port = _host_port(primary)
        if host:
            try:
                with socket.create_connection((host, port), timeout=2.0):
                    out["ok"] = True
                    out["active_endpoint"] = primary
            except OSError as exc:
                out["error"] = str(exc)[:200]
        return out
    host, port = _host_port(vip)
    if not host:
        out["error"] = "invalid MINIO_VIP"
        return out
    try:
        with socket.create_connection((host, port), timeout=2.0):
            out["ok"] = True
            out["active_endpoint"] = vip
    except OSError as exc:
        out["error"] = str(exc)[:200]
    return out
