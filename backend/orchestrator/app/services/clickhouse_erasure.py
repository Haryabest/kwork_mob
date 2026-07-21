"""Право на забвение в ClickHouse §12.6 / §12.7."""

from __future__ import annotations

import logging

from app.services.analytics_ingest import _ch

logger = logging.getLogger(__name__)

_CH_USER_TABLES = (
    "user_events",
    "mobile_analytics_events",
    "service_logs",
    "order_events",
    "publication_funnel_events",
)


def purge_user_data(user_id: int) -> dict:
    """ALTER TABLE … DELETE WHERE user_id (async mutations в CH)."""
    client = _ch()
    if client is None:
        return {"ok": False, "reason": "clickhouse_unavailable", "tables": []}
    uid = int(user_id)
    done: list[str] = []
    for table in _CH_USER_TABLES:
        try:
            client.command(f"ALTER TABLE {table} DELETE WHERE user_id = {uid}")
            done.append(table)
        except Exception as exc:  # noqa: BLE001
            logger.warning("CH erasure %s user=%s: %s", table, user_id, exc)
    return {"ok": bool(done), "tables": done}
