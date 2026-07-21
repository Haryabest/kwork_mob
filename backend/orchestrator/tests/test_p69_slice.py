"""§12.1 user_events taxonomy + PG table."""

from __future__ import annotations

import pytest

from app.services.user_events import USER_EVENT_TYPES, record_event


def test_user_event_taxonomy_30_plus():
    assert len(USER_EVENT_TYPES) >= 30
    assert "login" in USER_EVENT_TYPES
    assert "model_generated" in USER_EVENT_TYPES
    assert "company_invite_sent" in USER_EVENT_TYPES


@pytest.mark.asyncio
async def test_record_user_event(db):
    row = await record_event(
        db,
        event_type="login",
        user_id=None,
        payload={"method": "email", "success": True},
    )
    assert row.event_type == "login"
    await db.commit()


def test_user_events_ch_ddl():
    sql = (
        __import__("pathlib").Path(__file__).resolve().parents[3]
        / "infra"
        / "clickhouse"
        / "init.sql"
    ).read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS user_events" in sql
    assert "TTL event_ts + INTERVAL 1 YEAR" in sql


def test_admin_user_events_routes():
    from app.api.v1 import admin as adm

    paths = {getattr(r, "path", "") for r in adm.router.routes}
    assert "/user-events" in paths
    assert "/user-events/taxonomy" in paths
