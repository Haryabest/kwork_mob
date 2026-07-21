"""Redis Sentinel status §22.2.2."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.redis import _parse_sentinels


def redis_sentinel_status() -> dict[str, Any]:
    raw = (settings.REDIS_SENTINELS or "").strip()
    out: dict[str, Any] = {
        "configured": bool(raw),
        "master_name": settings.REDIS_SENTINEL_MASTER,
        "sentinels": [],
        "master": None,
        "ok": False,
    }
    if not raw:
        out["note"] = "REDIS_SENTINELS not set (single-node redis)"
        return out
    nodes = _parse_sentinels(raw)
    out["sentinels"] = [{"host": h, "port": p} for h, p in nodes]
    try:
        from redis.sentinel import Sentinel

        sentinel = Sentinel(
            nodes,
            socket_timeout=2.0,
            password=(settings.REDIS_SENTINEL_PASSWORD or settings.REDIS_PASSWORD or None),
        )
        master = sentinel.discover_master(settings.REDIS_SENTINEL_MASTER)
        slaves = sentinel.discover_slaves(settings.REDIS_SENTINEL_MASTER)
        out["master"] = {"host": master[0], "port": master[1]}
        out["slaves"] = [{"host": h, "port": p} for h, p in slaves]
        out["ok"] = True
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:200]
    return out
