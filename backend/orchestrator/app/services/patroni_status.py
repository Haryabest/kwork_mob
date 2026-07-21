"""Patroni cluster status §22.2.1."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


def patroni_status() -> dict[str, Any]:
    url = (getattr(settings, "PATRONI_REST_URL", "") or "http://patroni-1:8008").rstrip("/")
    out: dict[str, Any] = {"url": url, "ok": False, "role": None, "state": None, "members": []}
    try:
        with httpx.Client(timeout=3.0) as client:
            primary = client.get(f"{url}/primary")
            cluster = client.get(f"{url}/cluster")
        if primary.status_code == 200:
            body = primary.json()
            out["ok"] = True
            out["role"] = body.get("role") or body.get("state")
            out["state"] = body.get("state")
            out["member"] = body.get("member") or body.get("name")
        if cluster.status_code == 200:
            data = cluster.json()
            members = data.get("members") if isinstance(data, dict) else None
            if isinstance(members, list):
                out["members"] = members
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:200]
    return out
