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

    async def fake_threshold(_key, default):
        return 1000

    monkeypatch.setattr("app.services.analytics_sync.count_pending", fake_count)
    monkeypatch.setattr("app.services.alert_thresholds.threshold_async", fake_threshold)
    from app.services.analytics_query import analytics_sync_status

    class FakeDb:
        pass

    data = await analytics_sync_status(FakeDb())
    assert data["pending_ch_sync"] == 42
    assert data["alert"] is False
    assert data["alert_threshold"] == 1000


async def test_screen_timeseries_pg_fallback(monkeypatch):
    from app.services.analytics_query import screen_timeseries

    monkeypatch.setattr("app.services.analytics_query._screen_timeseries_ch", lambda **_: None)

    async def fake_pg(_db, *, days, top, screen=None):
        if screen:
            return [screen], [{"day": "2026-07-01", screen: 5}]
        return ["home"], [{"day": "2026-07-01", "home": 3}]

    monkeypatch.setattr("app.services.analytics_query._screen_timeseries_pg", fake_pg)
    data = await screen_timeseries(object(), days=7, top=5)
    assert data["source"] == "postgres"
    assert data["screens"] == ["home"]

    data2 = await screen_timeseries(object(), days=7, top=5, screen="queue")
    assert data2["screen"] == "queue"
    assert data2["screens"] == ["queue"]
