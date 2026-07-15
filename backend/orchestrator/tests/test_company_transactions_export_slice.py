"""Company transactions CSV export + push pref helpers."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.company_balance import transactions_to_csv
from app.services.push import user_wants_notification


def test_transactions_to_csv_header_and_row():
    row = SimpleNamespace(
        id=1,
        user_id=42,
        created_at=datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc),
        tx_type="charge",
        amount=-500,
        description="Заказ #7",
    )
    csv_text = transactions_to_csv([row])
    lines = csv_text.strip().splitlines()
    assert lines[0] == "id,user_id,date,type,amount,description"
    assert "42" in lines[1]
    assert "charge" in lines[1]
    assert "-500" in lines[1]


def test_user_wants_notification_respects_event_toggle():
    user = SimpleNamespace(notification_prefs={"refund": False, "push_enabled": True})
    assert user_wants_notification(user, "refund") is False
    assert user_wants_notification(user, "nsfw_blocked") is True


def test_user_wants_notification_master_off():
    user = SimpleNamespace(notification_prefs={"push_enabled": False, "email_enabled": False})
    assert user_wants_notification(user, "refund") is False
