"""PG → ClickHouse analytics sync §19.20."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MobileAnalyticsEvent
from app.services.analytics_ingest import _ch

logger = logging.getLogger(__name__)


def _insert_ch_rows(rows: list[MobileAnalyticsEvent]) -> bool:
    client = _ch()
    if client is None or not rows:
        return False
    payload = [
        {
            "user_id": r.user_id,
            "event": r.event,
            "event_ts": r.event_ts,
            "props": json.dumps(r.props or {}, ensure_ascii=False),
        }
        for r in rows
    ]
    try:
        client.insert(
            "mobile_analytics_events",
            payload,
            column_names=["user_id", "event", "event_ts", "props"],
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("analytics PG→CH sync insert failed: %s", exc)
        return False


async def count_pending(db: AsyncSession) -> int:
    return int(
        await db.scalar(
            select(func.count())
            .select_from(MobileAnalyticsEvent)
            .where(MobileAnalyticsEvent.ch_synced_at.is_(None))
        )
        or 0
    )


async def sync_unsynced(db: AsyncSession, *, limit: int = 500) -> dict:
    """Mirror PG rows with ch_synced_at IS NULL into ClickHouse."""
    rows = (
        await db.scalars(
            select(MobileAnalyticsEvent)
            .where(MobileAnalyticsEvent.ch_synced_at.is_(None))
            .order_by(MobileAnalyticsEvent.id)
            .limit(limit)
        )
    ).all()
    if not rows:
        pending = await count_pending(db)
        return {"synced": 0, "pending": pending, "ok": True}
    ok = _insert_ch_rows(list(rows))
    synced = 0
    if ok:
        now = datetime.now(timezone.utc)
        for row in rows:
            row.ch_synced_at = now
            synced += 1
        await db.flush()
    pending = await count_pending(db)
    return {"synced": synced, "pending": pending, "ok": ok}
