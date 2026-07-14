"""Unit checks for corporate / yookassa / shoot-link thresholds §12.4.1."""

from app.services import corporate_alerts as ca
from app.services import shoot_link_limits as sll
from app.services import yookassa_alerts as yk


def test_thresholds(monkeypatch):
    class S:
        YOOKASSA_ERROR_STREAK_ALERT = 5
        COMPANY_LOW_BALANCE_ALERT_RUB = 5000
        COMPANY_SUSPICIOUS_ORDERS_10M = 50
        COMPANY_SUSPICIOUS_WINDOW_MIN = 10
        SHOOT_LINK_MASS_LIMIT_PER_HOUR = 100
        SHOOT_LINK_MASS_BLOCK_HOURS = 1

    monkeypatch.setattr(yk, "settings", S())
    monkeypatch.setattr(ca, "settings", S())
    monkeypatch.setattr(sll, "settings", S())
    assert yk._threshold() == 5
    assert ca._low_balance_threshold() == 5000
    assert ca._suspicious_orders() == 50
    assert sll._limit_per_hour() == 100


def test_age_csv():
    from app.services import age_admin as aa

    csv_text = aa.to_csv(
        [
            {
                "id": 1,
                "user_id": 2,
                "email": "a@b.c",
                "age": 20,
                "success": True,
                "category": "adult",
                "created_at": "2026-01-01T00:00:00+00:00",
                "date_of_birth": "2000-01-01",
                "user_age_verified_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )
    assert "user_id" in csv_text
    assert "a@b.c" in csv_text
