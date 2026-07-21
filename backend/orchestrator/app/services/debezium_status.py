"""Debezium Connect status §12.1 PG→CH pipeline."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


def debezium_status() -> dict[str, Any]:
    base = (settings.DEBEZIUM_CONNECT_URL or "").rstrip("/")
    out: dict[str, Any] = {
        "url": base or None,
        "configured": bool(base),
        "sync_mode": settings.USER_EVENTS_SYNC_MODE,
        "ok": False,
        "connectors": [],
    }
    if not base:
        out["note"] = "Set DEBEZIUM_CONNECT_URL to enable CDC monitoring"
        return out
    try:
        with httpx.Client(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
            health = client.get(f"{base}/")
            out["connect_ok"] = health.status_code == 200
            names = client.get(f"{base}/connectors")
            if names.status_code == 200:
                connector_names = names.json()
                if isinstance(connector_names, list):
                    for name in connector_names:
                        item: dict[str, Any] = {"name": name}
                        st = client.get(f"{base}/connectors/{name}/status")
                        if st.status_code == 200:
                            body = st.json()
                            item["state"] = (body.get("connector") or {}).get("state")
                            tasks = body.get("tasks") or []
                            item["tasks"] = [
                                {"id": t.get("id"), "state": t.get("state")} for t in tasks
                            ]
                        out["connectors"].append(item)
            out["ok"] = bool(out.get("connect_ok")) and any(
                c.get("state") == "RUNNING" for c in out["connectors"]
            )
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:200]
    return out
