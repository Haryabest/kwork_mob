"""Unit checks for ops alerts thresholds (§12.4.1)."""

from app.services import ops_alerts as oa


def test_default_thresholds(monkeypatch):
    class S:
        QUEUE_ALERT_LENGTH = 20
        ALL_BUSY_ALERT_MINUTES = 5
        WORKER_OFFLINE_ALERT_SECONDS = 30

    monkeypatch.setattr(oa, "settings", S())
    assert oa._queue_threshold() == 20
    assert oa._all_busy_minutes() == 5
    assert oa._offline_seconds() == 30
