"""Admin analytics queries §19.20 — screen breakdown from ClickHouse / PG fallback."""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CampaignEntitlement, MobileAnalyticsEvent
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


async def list_raw_events(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 500,
    offset: int = 0,
) -> dict:
    filters = [MobileAnalyticsEvent.id.isnot(None)]
    if user_id is not None:
        filters.append(MobileAnalyticsEvent.user_id == user_id)
    if date_from is not None:
        filters.append(MobileAnalyticsEvent.event_ts >= date_from)
    if date_to is not None:
        filters.append(MobileAnalyticsEvent.event_ts <= date_to)
    total = int(
        await db.scalar(select(func.count()).select_from(MobileAnalyticsEvent).where(*filters)) or 0
    )
    rows = (
        await db.scalars(
            select(MobileAnalyticsEvent)
            .where(*filters)
            .order_by(MobileAnalyticsEvent.event_ts.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    items = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "event": r.event,
            "event_ts": r.event_ts.isoformat() if r.event_ts else None,
            "props": r.props,
            "ingested_at": r.ingested_at.isoformat() if r.ingested_at else None,
            "ch_synced_at": r.ch_synced_at.isoformat() if r.ch_synced_at else None,
        }
        for r in rows
    ]
    return {
        "user_id": user_id,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "limit": limit,
        "offset": offset,
        "total": total,
        "has_more": offset + len(items) < total,
        "items": items,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


def raw_events_to_csv(data: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "user_id", "event", "event_ts", "props", "ingested_at", "ch_synced_at"])
    for row in data.get("items") or []:
        w.writerow(
            [
                row.get("id"),
                row.get("user_id"),
                row.get("event"),
                row.get("event_ts"),
                json.dumps(row.get("props") or {}, ensure_ascii=False),
                row.get("ingested_at"),
                row.get("ch_synced_at"),
            ]
        )
    return buf.getvalue()


async def analytics_sync_status(db: AsyncSession) -> dict:
    from app.services.alert_thresholds import threshold_async
    from app.services.analytics_sync import count_pending

    pending = await count_pending(db)
    alert_threshold = int(await threshold_async("analytics_ch_sync_pending_max", 1000))
    alert = pending > alert_threshold
    return {
        "pending_ch_sync": pending,
        "alert": alert,
        "alert_threshold": alert_threshold,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


def _campaign_banner_ctr_ch(*, days: int) -> dict[int, dict] | None:
    client = _ch()
    if client is None:
        return None
    try:
        result = client.query(
            """
            SELECT
                banner_id,
                screen,
                sum(events) AS cnt
            FROM mobile_analytics_banner_daily
            WHERE day >= today() - %(days)s
            GROUP BY banner_id, screen
            """,
            parameters={"days": days},
        )
        banner_stats: dict[int, dict[str, int]] = {}
        for r in result.result_rows or []:
            bid, screen, cnt = int(r[0]), str(r[1]), int(r[2])
            if bid <= 0:
                continue
            banner_stats.setdefault(bid, {"impressions": 0, "clicks": 0})
            if screen == "campaign_banner":
                banner_stats[bid]["impressions"] += cnt
            elif screen == "campaign_banner_click":
                banner_stats[bid]["clicks"] += cnt
        return banner_stats
    except Exception as exc:  # noqa: BLE001
        logger.debug("CH campaign banner CTR failed: %s", exc)
        return None


async def _campaign_banner_ctr_pg(db: AsyncSession, *, days: int) -> dict[int, dict[str, int]]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    screen_col = MobileAnalyticsEvent.props["screen"].astext
    banner_col = MobileAnalyticsEvent.props["banner_id"].as_integer()
    rows = (
        await db.execute(
            select(
                CampaignEntitlement.campaign_id,
                screen_col.label("screen"),
                func.count().label("cnt"),
            )
            .join(CampaignEntitlement, CampaignEntitlement.id == banner_col)
            .where(
                MobileAnalyticsEvent.event == "screen_view",
                MobileAnalyticsEvent.event_ts >= since,
                screen_col.in_(["campaign_banner", "campaign_banner_click"]),
                banner_col.isnot(None),
            )
            .group_by(CampaignEntitlement.campaign_id, screen_col)
        )
    ).all()
    out: dict[int, dict[str, int]] = {}
    for r in rows:
        cid = int(r.campaign_id)
        out.setdefault(cid, {"impressions": 0, "clicks": 0})
        if r.screen == "campaign_banner":
            out[cid]["impressions"] += int(r.cnt)
        elif r.screen == "campaign_banner_click":
            out[cid]["clicks"] += int(r.cnt)
    return out


async def campaign_banner_ctr(
    db: AsyncSession,
    *,
    days: int = 30,
    campaign_ids: list[int] | None = None,
) -> dict:
    """In-app banner impressions/clicks по campaign_id §19.20."""
    banner_stats = _campaign_banner_ctr_ch(days=days)
    source = "clickhouse"
    by_campaign: dict[int, dict[str, int]] = {}
    if banner_stats is None:
        by_campaign = await _campaign_banner_ctr_pg(db, days=days)
        source = "postgres"
    else:
        if banner_stats:
            ent_rows = (
                await db.execute(
                    select(CampaignEntitlement.id, CampaignEntitlement.campaign_id).where(
                        CampaignEntitlement.id.in_(list(banner_stats.keys()))
                    )
                )
            ).all()
            ent_map = {int(r.id): int(r.campaign_id) for r in ent_rows}
            for bid, stats in banner_stats.items():
                cid = ent_map.get(bid)
                if cid is None:
                    continue
                by_campaign.setdefault(cid, {"impressions": 0, "clicks": 0})
                by_campaign[cid]["impressions"] += stats.get("impressions", 0)
                by_campaign[cid]["clicks"] += stats.get("clicks", 0)
    if campaign_ids is not None:
        by_campaign = {cid: by_campaign.get(cid, {"impressions": 0, "clicks": 0}) for cid in campaign_ids}
    items = []
    for cid, stats in sorted(by_campaign.items()):
        imp = stats.get("impressions", 0)
        clk = stats.get("clicks", 0)
        items.append(
            {
                "campaign_id": cid,
                "impressions": imp,
                "clicks": clk,
                "ctr": round(clk / imp, 4) if imp else 0.0,
            }
        )
    return {
        "days": days,
        "source": source,
        "items": items,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


def _screen_timeseries_ch(
    *, days: int, top: int, screen: str | None = None
) -> tuple[list[str], list[dict]] | None:
    client = _ch()
    if client is None:
        return None
    try:
        if screen:
            screens = [screen]
            series_rows = client.query(
                """
                SELECT day, sum(events) AS views
                FROM mobile_analytics_screen_daily
                WHERE day >= today() - %(days)s AND screen = %(screen)s
                GROUP BY day
                ORDER BY day
                """,
                parameters={"days": days, "screen": screen},
            ).result_rows or []
            series = [
                {"day": str(day), screen: int(views)}
                for day, views in series_rows
            ]
            return screens, series
        top_rows = client.query(
            """
            SELECT screen, sum(events) AS views
            FROM mobile_analytics_screen_daily
            WHERE day >= today() - %(days)s
            GROUP BY screen
            ORDER BY views DESC
            LIMIT %(top)s
            """,
            parameters={"days": days, "top": top},
        ).result_rows or []
        screens = [str(r[0]) for r in top_rows if r[0]]
        if not screens:
            return [], []
        series_rows = client.query(
            """
            SELECT day, screen, sum(events) AS views
            FROM mobile_analytics_screen_daily
            WHERE day >= today() - %(days)s
              AND screen IN %(screens)s
            GROUP BY day, screen
            ORDER BY day, screen
            """,
            parameters={"days": days, "screens": screens},
        ).result_rows or []
        by_day: dict[str, dict[str, int]] = {}
        for day, screen, views in series_rows:
            key = str(day)
            by_day.setdefault(key, {})[str(screen)] = int(views)
        series = [{"day": day, **vals} for day, vals in sorted(by_day.items())]
        return screens, series
    except Exception as exc:  # noqa: BLE001
        logger.debug("CH screen timeseries failed: %s", exc)
        return None


async def _screen_timeseries_pg(
    db: AsyncSession, *, days: int, top: int, screen: str | None = None
) -> tuple[list[str], list[dict]]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    screen_col = MobileAnalyticsEvent.props["screen"].astext
    day_col = func.date_trunc("day", MobileAnalyticsEvent.event_ts)
    if screen:
        rows = (
            await db.execute(
                select(day_col.label("day"), func.count().label("views"))
                .where(
                    MobileAnalyticsEvent.event == "screen_view",
                    MobileAnalyticsEvent.event_ts >= since,
                    screen_col == screen,
                )
                .group_by(day_col)
                .order_by(day_col)
            )
        ).all()
        series = [
            {"day": r.day.date().isoformat() if r.day else "", screen: int(r.views)} for r in rows
        ]
        return [screen], series
    top_rows = (
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
            .limit(top)
        )
    ).all()
    screens = [str(r.screen) for r in top_rows if r.screen]
    if not screens:
        return [], []
    rows = (
        await db.execute(
            select(day_col.label("day"), screen_col.label("screen"), func.count().label("views"))
            .where(
                MobileAnalyticsEvent.event == "screen_view",
                MobileAnalyticsEvent.event_ts >= since,
                screen_col.in_(screens),
            )
            .group_by(day_col, screen_col)
            .order_by(day_col, screen_col)
        )
    ).all()
    by_day: dict[str, dict[str, int]] = {}
    for r in rows:
        day = r.day.date().isoformat() if r.day else ""
        by_day.setdefault(day, {})[str(r.screen)] = int(r.views)
    series = [{"day": day, **vals} for day, vals in sorted(by_day.items())]
    return screens, series


async def screen_timeseries(
    db: AsyncSession, *, days: int = 14, top: int = 8, screen: str | None = None
) -> dict:
    ch = _screen_timeseries_ch(days=days, top=top, screen=screen)
    source = "clickhouse"
    if ch is None:
        screens, series = await _screen_timeseries_pg(db, days=days, top=top, screen=screen)
        source = "postgres"
    else:
        screens, series = ch
    return {
        "days": days,
        "top": top,
        "screen": screen,
        "source": source,
        "screens": screens,
        "series": series,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
