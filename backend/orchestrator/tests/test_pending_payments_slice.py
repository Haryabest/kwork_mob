"""Pending YooKassa payments slice §20.3.4."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.pending_payments import merge_transaction_page, pending_status_label, pending_to_dict


def test_pending_to_dict_status():
    row = SimpleNamespace(
        payment_id="pay-1",
        user_id=1,
        company_id=None,
        amount=1000,
        payment_method="sbp_qr",
        status="pending",
        created_at=datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc),
    )
    d = pending_to_dict(row)
    assert d["status"] == "pending"
    assert d["status_label"] == "В обработке"
    assert d["pending"] is True
    assert "СБП" in d["description"]


def test_pending_status_label_failed():
    assert pending_status_label("canceled") == "Ошибка"


def test_merge_transaction_page_prepends_pending():
    pending = [{"id": "pending:p1", "created_at": "2026-07-15T12:00:00+00:00"}]
    tx = [{"id": 1, "created_at": "2026-07-14T12:00:00+00:00"}]
    page, total = merge_transaction_page(
        tx_items=tx,
        pending_items=pending,
        tx_total=1,
        limit=20,
        offset=0,
    )
    assert total == 2
    assert page[0]["id"] == "pending:p1"
    assert page[1]["id"] == 1
