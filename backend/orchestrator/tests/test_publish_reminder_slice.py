"""Publish reminder §7.5.3."""

from app.services import publish_reminder as pr


def test_reminder_days():
    assert 3 in pr.REMINDER_DAYS and 14 in pr.REMINDER_DAYS


def test_needs_publish_reminder():
    assert pr.needs_publish_reminder("not_published") is True
    assert pr.needs_publish_reminder(None) is True
    assert pr.needs_publish_reminder("published_ozon") is False
    assert pr.needs_publish_reminder("verified_wb") is False
    assert pr.needs_publish_reminder("api_uploaded_wb") is False


def test_reminder_copy():
    t3, b3 = pr.reminder_copy(3)
    t14, b14 = pr.reminder_copy(14)
    assert "бонус" in b3.lower()
    assert "поддерж" in b14.lower() or "помощ" in b14.lower()
    assert t3 and t14
