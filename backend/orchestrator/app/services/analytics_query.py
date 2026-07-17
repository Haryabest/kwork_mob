"""Admin analytics queries §19.20 — screen breakdown from ClickHouse / PG fallback."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MobileAnalyticsEvent
from app.services.analytics_ingest import _ch

logger = logging.getLogger(__name__)


def _screen_breakdown_ch(*, days: int, limit: int) -> list[dict] | None:
    client = _ch()
    if client is None:
        return None
    try:
        result = client.query(
            """
            SELECT screen, sum(events) AS views
            FROM mobile_analytics_screen_daily
            WHERE day >= today() - %(days)s
            GROUP BY screen
            ORDER BY views DESC
            LIMIT %(limit)s
            """,
            parameters={"days": days, "limit": limit},
        )
        rows = result.result_rows or []
        return [{"screen": str(r[0]), "views": int(r[1])} for r in rows if r[0]]
    except Exception as exc:  # noqa: BLE001
        logger.debug("CH screen breakdown failed: %s", exc)
        return None


async def _screen_breakdown_pg(db: AsyncSession, *, days: int, limit: int) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    screen_col = MobileAnalyticsEvent.props["screen"].astext
    rows = (
        await db.execute(
            select(screen_col.label("screen"), func.count().label("views"))
            .where(
                MobileAnalyticsEvent.event == "screen_view",
                MobileAnalyticsEvent.event_ts >= since,
                screen_col.isnot(None),
                screen_col != "",
            )
            .group_by(screen_col)
            .order_by(func.count().desc())
            .limit(limit)
        )
    ).all()
    return [{"screen": str(r.screen), "views": int(r.views)} for r in rows]


async def screen_breakdown(db: AsyncSession, *, days: int = 7, limit: int = 50) -> dict:
    items = _screen_breakdown_ch(days=days, limit=limit)
    source = "clickhouse"
    if items is None:
        items = await _screen_breakdown_pg(db, days=days, limit=limit)
        source = "postgres"
    total = sum(i["views"] for i in items)
    return {
        "days": days,
        "limit": limit,
        "total_views": total,
        "source": source,
        "items": items,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


def screens_to_csv(data: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["screen", "views"])
    for row in data.get("items") or []:
        w.writerow([row.get("screen", ""), row.get("views", 0)])
    return buf.getvalue()
