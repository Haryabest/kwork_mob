"""YooKassa webhook auth + email recipients + support ticket helpers."""

from types import SimpleNamespace

from app.services import alerts as alerts_svc
from app.services import yookassa_webhook_auth as yka


def test_yookassa_official_ip():
    assert yka.is_yookassa_ip("185.71.76.1") is True
    assert yka.is_yookassa_ip("77.75.156.11") is True
    assert yka.is_yookassa_ip("8.8.8.8") is False


def test_normalize_email_recipients_max_5():
    csv, lst = alerts_svc.normalize_email_recipients(
        ["a@x.com", "b@x.com", "c@x.com", "d@x.com", "e@x.com", "f@x.com"]
    )
    assert len(lst) == 5
    assert "f@x.com" not in lst
    assert csv and "a@x.com" in csv


def test_email_recipients_from_cfg():
    cfg = SimpleNamespace(
        email_to="one@x.com, two@x.com",
        thresholds={"email_recipients": ["three@x.com", "one@x.com"]},
    )
    rec = alerts_svc._email_recipients(cfg)
    assert rec[0] == "three@x.com"
    assert "one@x.com" in rec
    assert len(rec) <= 5


def test_assert_payment_authentic_ok():
    yka.assert_payment_authentic(
        payment={"id": "pay-1", "recipient": {"account_id": "shop"}},
        payment_id="pay-1",
        expected_shop_id="shop",
    )


def test_assert_payment_authentic_mismatch():
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        yka.assert_payment_authentic(
            payment={"id": "other", "recipient": {"account_id": "shop"}},
            payment_id="pay-1",
            expected_shop_id="shop",
        )
