"""Analytics PG→CH sync §19.20."""

from types import SimpleNamespace

import pytest

from app.services.analytics_sync import sync_unsynced

pytestmark = pytest.mark.asyncio


async def test_sync_unsynced_marks_rows(monkeypatch):
    row = SimpleNamespace(
        id=1,
        user_id=2,
        event="screen_view",
        event_ts=None,
        props={"screen": "home"},
        ch_synced_at=None,
    )

    class FakeDb:
        def __init__(self):
            self.flushed = 0

        async def scalars(self, stmt):
            class R:
                def all(self):
                    if self._pass == 1:
                        self._pass = 2
                        return [row]
                    return []

                _pass = 1

            return R()

        async def scalar(self, *_a, **_k):
            return None

        async def flush(self):
            self.flushed += 1

    monkeypatch.setattr("app.services.analytics_sync._insert_ch_rows", lambda rows: True)
    db = FakeDb()
    result = await sync_unsynced(db, limit=10)
    assert result["synced"] == 1
    assert row.ch_synced_at is not None
