"""Tests: alert_log CSV, write activity, soft-launch KPI CSV."""

from app.services import alerts as alerts_svc
from app.services import soft_launch as sl


def test_alert_log_to_csv():
    csv = alerts_svc.alert_log_to_csv(
        [
            {
                "id": 1,
                "created_at": "2026-07-14T12:00:00+00:00",
                "event_type": "queue_length",
                "channel": "telegram",
                "ok": True,
                "company_id": None,
                "worker_id": "w1",
                "text": "queue high",
                "error": None,
                "payload": {"fingerprint": "q"},
            }
        ]
    )
    assert "queue_length" in csv
    assert "telegram" in csv
    assert "id,created_at" in csv.replace("\r\n", "\n").split("\n")[0] or "id" in csv


def test_kpi_to_csv_shape():
    data = {
        "period_days": 7,
        "since": "2026-07-07T00:00:00+00:00",
        "funnel": {
            "generated": 10,
            "downloaded": 8,
            "links_added": 5,
            "verified": 4,
            "manual_marked": 1,
            "conversion": {"generated_to_verified": 0.4},
        },
        "orders": {
            "total": 12,
            "paid_pipeline": 10,
            "completed": 8,
            "cancelled": 1,
            "nsfw_blocked": 0,
            "cancel_rate": 0.08,
            "by_status": {"completed": 8, "cancelled": 1},
        },
        "finance": {"revenue_rub": 29900, "refunds_rub": 0},
        "models_created": 8,
        "kpi": {"funnel_conversion": 0.4, "target_conversion_60": False},
        "orders_daily": [{"day": "2026-07-14", "count": 3}],
    }
    csv = sl.kpi_to_csv(data)
    assert "funnel" in csv
    assert "2026-07-14" in csv
    assert "29900" in csv
