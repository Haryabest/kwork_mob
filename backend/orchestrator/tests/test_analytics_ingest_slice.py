"""Analytics ingest persistence §19.20."""

from types import SimpleNamespace

from app.schemas.analytics import AnalyticsEventItem
from app.services.analytics_ingest import _parse_ts, persist_events


def test_parse_ts_zulu():
    ts = _parse_ts("2026-07-17T10:00:00Z")
    assert ts.tzinfo is not None
    assert ts.year == 2026


def test_persist_events_writes_rows():
    user = SimpleNamespace(id=42)
    events = [
        AnalyticsEventItem(
            event="screen_view",
            ts="2026-07-17T10:00:00Z",
            props={"screen": "balance"},
        )
    ]

    async def _run():
        class FakeDb:
            def __init__(self):
                self.rows = []

            def add(self, row):
                self.rows.append(row)

            async def flush(self):
                return None

        db = FakeDb()
        n = await persist_events(db, user, events)
        assert n == 1
        assert len(db.rows) == 1
        assert db.rows[0].event == "screen_view"
        assert db.rows[0].user_id == 42

    import asyncio

    asyncio.run(_run())
