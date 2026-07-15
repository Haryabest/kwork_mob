"""Notification inbox API slice."""

from app.services.notification_inbox import MAX_INBOX


def test_max_inbox_constant():
    assert MAX_INBOX == 200
