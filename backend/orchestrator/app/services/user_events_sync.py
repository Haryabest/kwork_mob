"""PG → ClickHouse user_events sync §12.1 / §12.2."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserEvent
from app.services.analytics_ingest import _ch

logger = logging.getLogger(__name__)


def _insert_ch_rows(rows: list[UserEvent]) -> bool:
    client = _ch()
    if client is None or not rows:
        return False
    payload = [
        {
            "event_id": str(r.event_id),
            "user_id": int(r.user_id or 0),
            "company_id": r.company_id,
            "member_role": r.member_role or "",
            "event_type": r.event_type,
            "event_ts": r.created_at,
            "payload": json.dumps(r.payload or {}, ensure_ascii=False),
        }
        for r in rows
    ]
    try:
        client.insert(
            "user_events",
            payload,
            column_names=[
                "event_id",
                "user_id",
                "company_id",
                "member_role",
                "event_type",
                "event_ts",
                "payload",
            ],
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("user_events PG→CH sync failed: %s", exc)
        return False


async def count_pending(db: AsyncSession) -> int:
    return int(
        await db.scalar(
            select(func.count()).select_from(UserEvent).where(UserEvent.ch_synced_at.is_(None))
        )
        or 0
    )


async def sync_unsynced(db: AsyncSession, *, limit: int = 500) -> dict:
    from app.core.config import settings

    mode = (settings.USER_EVENTS_SYNC_MODE or "celery").lower()
    if mode == "debezium":
        pending = await count_pending(db)
        return {"synced": 0, "pending": pending, "ok": True, "skipped": "debezium"}
    rows = (
        await db.scalars(
            select(UserEvent)
            .where(UserEvent.ch_synced_at.is_(None))
            .order_by(UserEvent.id)
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
