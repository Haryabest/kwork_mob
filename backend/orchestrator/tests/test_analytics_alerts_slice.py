"""Analytics CH sync alerts §19.20."""

import pytest

from app.services import analytics_alerts as aa

pytestmark = pytest.mark.asyncio


async def test_check_and_alert_below_threshold(monkeypatch):
    async def fake_count(_db):
        return 10

    monkeypatch.setattr("app.services.analytics_alerts.count_pending", fake_count)
    result = await aa.check_and_alert(object())
    assert result["alert_sent"] is False
    assert result["pending_ch_sync"] == 10


async def test_check_and_alert_sends(monkeypatch):
    async def fake_count(_db):
        return 2000

    sent = {}

    async def fake_dual(db, text, **kwargs):
        sent["text"] = text
        return {"telegram": True, "email": False}

    async def fake_recent(_db, _fp):
        return False

    monkeypatch.setattr("app.services.analytics_alerts.count_pending", fake_count)
    monkeypatch.setattr("app.services.analytics_alerts._recent_ok", fake_recent)
    monkeypatch.setattr("app.services.analytics_alerts.alerts_svc.send_dual", fake_dual)
    result = await aa.check_and_alert(object())
    assert result["alert_sent"] is True
    assert "2000" in sent["text"]
