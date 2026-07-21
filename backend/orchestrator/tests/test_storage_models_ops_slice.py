"""Node timeline, disk forecast, model storage extend/trash."""

from datetime import datetime, timedelta, timezone

from app.services import model_storage as ms
from app.services.node_timeline import _node_status
from app.services.company_webhooks import delivery_dashboard  # noqa: F401 — import check


def test_node_status_offline():
    assert _node_status({"last_seen_age_sec": 120}) == "offline"
    assert _node_status({"last_seen_age_sec": 10}) == "online"


def test_storage_meta_extends():
    from types import SimpleNamespace

    model = SimpleNamespace(
        source_expires_at=datetime.now(timezone.utc) + timedelta(days=5),
        source_extend_count=1,
        trashed_at=None,
        created_at=datetime.now(timezone.utc) - timedelta(days=25),
    )
    meta = ms.storage_meta(model)  # type: ignore[arg-type]
    assert meta["extends_remaining"] == 2
    assert meta["max_extends"] == 3
    assert meta["days_left"] >= 4


def test_timeline_csv():
    from app.services.node_timeline import timeline_to_csv

    data = {
        "nodes": [
            {
                "node_id": "n1",
                "node_name": "Node 1",
                "offline_percent": 1.0,
                "uptime_percent": 99.0,
                "segments": [
                    {
                        "status": "online",
                        "started_at": "2026-07-01T00:00:00+00:00",
                        "ended_at": "2026-07-01T01:00:00+00:00",
                        "duration_sec": 3600,
                        "open": False,
                    }
                ],
            }
        ]
    }
    csv_text = timeline_to_csv(data)
    assert "node_id" in csv_text
    assert "n1" in csv_text
    assert "online" in csv_text


def test_mass_extend_limit():
    assert ms.MAX_EXTENDS == 3
    assert ms.TRASH_DAYS == 30


def test_default_expires():
    exp = ms.default_expires_at(datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert exp.year == 2026
    assert (exp - datetime(2026, 1, 1, tzinfo=timezone.utc)).days == ms.ttl_days()
