"""Analytics query service §19.20."""

from types import SimpleNamespace

import pytest

from app.services.analytics_query import screen_breakdown, screens_to_csv

pytestmark = pytest.mark.asyncio


def test_screens_to_csv():
    body = screens_to_csv({"items": [{"screen": "home", "views": 10}]})
    assert "home" in body
    assert "10" in body


async def test_screen_breakdown_pg_fallback(monkeypatch):
    class FakeDb:
        async def execute(self, *_a, **_k):
            class R:
                def all(self):
                    return [SimpleNamespace(screen="queue", views=3)]

            return R()

    monkeypatch.setattr("app.services.analytics_query._screen_breakdown_ch", lambda **_: None)
    data = await screen_breakdown(FakeDb(), days=7, limit=10)
    assert data["source"] == "postgres"
    assert data["items"][0]["screen"] == "queue"


async def test_analytics_sync_status(monkeypatch):
    async def fake_count(_db):
        return 42

    monkeypatch.setattr("app.services.analytics_sync.count_pending", fake_count)
    from app.services.analytics_query import analytics_sync_status

    class FakeDb:
        pass

    data = await analytics_sync_status(FakeDb())
    assert data["pending_ch_sync"] == 42
    assert data["alert"] is False
