"""Witness quorum status §22.5."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


def witness_status() -> dict[str, Any]:
    url = (settings.WITNESS_URL or "http://ha-witness:8089/quorum").rstrip("/")
    if not url.endswith("/quorum"):
        url = f"{url}/quorum"
    out: dict[str, Any] = {"url": url, "ok": False}
    try:
        with httpx.Client(timeout=httpx.Timeout(1.0, connect=0.5)) as client:
            r = client.get(url)
        if r.status_code == 200:
            body = r.json()
            out.update(body)
            out["ok"] = bool(body.get("quorum_ok"))
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:200]
    return out
