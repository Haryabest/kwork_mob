"""Unit: age gate + watermark hmac."""

from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.services.age_gate import age_years, parse_birth_date
from app.services.watermark import verify_hmac_payload


def test_age_years():
    assert age_years(date(2000, 1, 1), today=date(2026, 7, 12)) >= 18
    assert age_years(date.today() - timedelta(days=365 * 17), today=date.today()) < 18


def test_parse_birth_date():
    assert parse_birth_date("2000-05-01") == date(2000, 5, 1)
    with pytest.raises(HTTPException):
        parse_birth_date("not-a-date")


def test_watermark_hmac(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "WATERMARK_HMAC_SECRET", "test-secret")
    assert verify_hmac_payload(1, None, 2, 100, "deadbeef") is False
    import hashlib
    import hmac

    payload = "1:0:2:100"
    digest = hmac.new(b"test-secret", payload.encode(), hashlib.sha256).hexdigest()
    assert verify_hmac_payload(1, None, 2, 100, digest) is True
