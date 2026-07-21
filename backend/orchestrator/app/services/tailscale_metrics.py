"""Tailscale connectivity sidecar §23.3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import settings


def tailscale_status() -> dict[str, Any]:
    path = (getattr(settings, "TAILSCALE_STATUS_JSON", "") or "").strip()
    out: dict[str, Any] = {"configured": bool(path), "peers": [], "self": None, "ok": False}
    if not path:
        out["note"] = "TAILSCALE_STATUS_JSON not set"
        return out
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            out["self"] = data.get("Self") or data.get("self")
            peers = data.get("Peer") or data.get("peers") or {}
            if isinstance(peers, dict):
                out["peers"] = [
                    {
                        "hostname": p.get("HostName") or p.get("hostname"),
                        "online": p.get("Online") if "Online" in p else p.get("online"),
                        "tailscale_ips": p.get("TailscaleIPs") or p.get("tailscale_ips"),
                    }
                    for p in peers.values()
                    if isinstance(p, dict)
                ]
            out["ok"] = True
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:200]
    return out
