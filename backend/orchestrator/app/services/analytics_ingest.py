"""Persist mobile analytics events §19.20 — PostgreSQL + ClickHouse mirror."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import MobileAnalyticsEvent, User
from app.schemas.analytics import AnalyticsEventItem

logger = logging.getLogger(__name__)

_ch_client = None


def _ch():
    global _ch_client
    if _ch_client is not None:
        return _ch_client if _ch_client is not False else None
    try:
        import clickhouse_connect

        _ch_client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=int(settings.CLICKHOUSE_PORT),
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD or "",
            database=settings.CLICKHOUSE_DB,
        )
        return _ch_client
    except Exception as exc:  # noqa: BLE001
        logger.debug("ClickHouse analytics writer unavailable: %s", exc)
        _ch_client = False
        return None


def _parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)


def _write_clickhouse(*, user_id: int, rows: list[dict]) -> None:
    client = _ch()
    if client is None or not rows:
        return
    try:
        client.insert(
            "mobile_analytics_events",
            rows,
            column_names=["user_id", "event", "event_ts", "props"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("ClickHouse mobile_analytics_events insert failed: %s", exc)


async def persist_events(
    db: AsyncSession,
    user: User,
    events: list[AnalyticsEventItem],
) -> int:
    if not events:
        return 0
    ch_rows: list[dict] = []
    for item in events:
        ts = _parse_ts(item.ts)
        props = dict(item.props or {})
        db.add(
            MobileAnalyticsEvent(
                user_id=user.id,
                event=item.event,
                event_ts=ts,
                props=props or None,
            )
        )
        ch_rows.append(
            {
                "user_id": user.id,
                "event": item.event,
                "event_ts": ts,
                "props": json.dumps(props, ensure_ascii=False),
            }
        )
    await db.flush()
    _write_clickhouse(user_id=user.id, rows=ch_rows)
    return len(events)
