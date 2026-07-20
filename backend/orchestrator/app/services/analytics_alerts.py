"""Analytics PG→CH backlog alerts §19.20 / §12.4."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlertLog
from app.services import alerts as alerts_svc
from app.services.analytics_sync import count_pending

logger = logging.getLogger(__name__)

EVENT = "analytics_ch_sync_backlog"
COOLDOWN = timedelta(hours=1)
DEFAULT_THRESHOLD = 1000


async def _recent_ok(db: AsyncSession, fingerprint: str) -> bool:
    since = datetime.now(timezone.utc) - COOLDOWN
    rows = (
        await db.scalars(
            select(AlertLog)
            .where(
                AlertLog.event_type == EVENT,
                AlertLog.ok.is_(True),
                AlertLog.created_at >= since,
            )
            .order_by(AlertLog.id.desc())
            .limit(20)
        )
    ).all()
    return any((r.payload or {}).get("fingerprint") == fingerprint for r in rows)


async def check_and_alert(db: AsyncSession, *, threshold: int = DEFAULT_THRESHOLD) -> dict[str, Any]:
    """Telegram + email если pending_ch_sync > threshold (cooldown 1ч)."""
    pending = await count_pending(db)
    if pending <= threshold:
        return {"pending_ch_sync": pending, "threshold": threshold, "alert_sent": False}
    fp = f"pending_ge_{threshold}"
    if await _recent_ok(db, fp):
        return {
            "pending_ch_sync": pending,
            "threshold": threshold,
            "alert_sent": False,
            "reason": "cooldown",
        }
    text = (
        f"⚠️ Analytics PG→CH backlog\n"
        f"pending_ch_sync: {pending}\n"
        f"threshold: {threshold}\n"
        f"Проверьте Celery sync_analytics_to_clickhouse"
    )
    dual = await alerts_svc.send_dual(
        db,
        text,
        event_type=EVENT,
        payload={"fingerprint": fp, "pending_ch_sync": pending, "threshold": threshold},
        subject="[3dvektor] Analytics CH sync backlog",
        telegram=True,
        email=True,
    )
    sent = bool(dual.get("telegram") or dual.get("email"))
    return {
        "pending_ch_sync": pending,
        "threshold": threshold,
        "alert_sent": sent,
        "channels": dual,
    }
