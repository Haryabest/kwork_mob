"""§5 TRELLIS production readiness (P14)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import WorkerNode


async def trellis_prod_status(db: AsyncSession) -> dict[str, Any]:
    rows = (await db.scalars(select(WorkerNode).order_by(WorkerNode.id))).all()
    now = datetime.now(timezone.utc)
    nodes: list[dict[str, Any]] = []
    trellis_online = 0
    for w in rows:
        meta = dict(w.meta or {})
        caps = meta.get("capabilities") or []
        pipeline = str(meta.get("pipeline_mode") or meta.get("WORKER_PIPELINE_MODE") or "").lower()
        has_trellis = "trellis2" in caps or "trellis" in caps or pipeline == "trellis"
        hb = w.last_heartbeat
        fresh = False
        if hb:
            fresh = (now - hb).total_seconds() < 120
        online = w.status in ("idle", "busy", "online") and fresh
        if has_trellis and online:
            trellis_online += 1
        nodes.append(
            {
                "worker_id": w.id,
                "status": w.status,
                "gpu_name": w.gpu_name,
                "has_trellis": has_trellis,
                "online": online,
                "capabilities": caps[:8],
            }
        )
    return {
        "environment": settings.ENVIRONMENT,
        "workers_total": len(nodes),
        "trellis_online": trellis_online,
        "production_ready": trellis_online >= 1,
        "workers": nodes,
        "requirements": {
            "WORKER_PIPELINE_MODE": "trellis",
            "TRELLIS_ALLOW_STUB_FALLBACK": "0",
            "ENVIRONMENT": "production",
        },
        "e2e_script": "worker/scripts/e2e_trellis_acceptance.py",
        "note": "UNVERIFIED until GPU e2e acceptance on staging/prod",
    }
