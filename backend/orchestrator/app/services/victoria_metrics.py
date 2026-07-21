"""VictoriaMetrics long-term metrics §23.1."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


def victoria_status() -> dict[str, Any]:
    base = (settings.VICTORIA_METRICS_URL or "http://victoriametrics:8428").rstrip("/")
    out: dict[str, Any] = {"url": base, "ok": False}
    try:
        with httpx.Client(timeout=httpx.Timeout(1.0, connect=0.5)) as client:
            health = client.get(f"{base}/health")
            flags = client.get(f"{base}/flags")
        out["health"] = health.text.strip() if health.status_code == 200 else health.text[:100]
        out["ok"] = health.status_code == 200 and "ok" in (health.text or "").lower()
        if flags.status_code == 200:
            out["remote_write_ready"] = True
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:200]
    return out
