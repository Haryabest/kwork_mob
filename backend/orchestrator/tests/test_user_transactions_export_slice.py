"""User transactions CSV export slice §20.3.4."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.company_balance import merge_csv, transaction_status


def test_merge_csv_includes_pending_row():
    tx = SimpleNamespace(
        id=1,
        user_id=7,
        created_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        tx_type="charge",
        amount=-100,
        description="Заказ",
    )
    pending = [
        {
            "id": "pending:pay-1",
            "user_id": 7,
            "created_at": "2026-07-15T12:00:00+00:00",
            "type": "topup",
            "amount": 1000,
            "status_label": "В обработке",
            "description": "Пополнение через СБП",
        }
    ]
    csv_text = merge_csv([tx], pending)
    lines = csv_text.strip().splitlines()
    assert "status" in lines[0]
    assert "pending:pay-1" in lines[1]
    assert "charge" in lines[2]
    assert transaction_status(tx) == "succeeded"
