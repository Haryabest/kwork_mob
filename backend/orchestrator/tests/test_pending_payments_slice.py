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
    assert pending_status_label("failed") == "Ошибка"


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


def test_purge_old_settled_smoke():
    from app.services.pending_payments import purge_old_settled

    assert callable(purge_old_settled)


def test_refresh_stale_waiting_capture_smoke():
    from app.services.pending_payments import refresh_stale_waiting_capture

    assert callable(refresh_stale_waiting_capture)


def test_notify_topup_failed_smoke():
    from app.services.pending_payments import notify_topup_failed

    assert callable(notify_topup_failed)


def test_record_pending_poll_metrics():
    from app.services.metrics import PENDING_POLL_TOTAL, record_pending_poll

    before = PENDING_POLL_TOTAL.labels(outcome="settled")._value.get()  # noqa: SLF001
    record_pending_poll({"settled": 2, "failed": 1, "checked": 0})
    after = PENDING_POLL_TOTAL.labels(outcome="settled")._value.get()  # noqa: SLF001
    assert after >= before + 2


def test_settle_succeeded_topup_skips_bad_meta():
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from app.services.pending_payments import settle_succeeded_topup

    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)
    db.get = AsyncMock(return_value=None)
    db.add = MagicMock()
    db.flush = AsyncMock()

    result = asyncio.run(settle_succeeded_topup(db, {"id": "p1", "metadata": {}}))
    assert result == "skipped"
