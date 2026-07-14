"""Thresholds: redlock / webhook / api daily / escalation dual."""

from app.services import api_key_limits as akl
from app.services import yookassa_webhook_alerts as yk_wh


def test_daily_and_webhook_thresholds(monkeypatch):
    class S:
        API_KEY_DEFAULT_DAILY_LIMIT = 100_000
        YOOKASSA_WEBHOOK_FAIL_STREAK = 5
        COMPANY_WEBHOOK_FAIL_STREAK = 3

    monkeypatch.setattr(akl, "settings", S())
    monkeypatch.setattr(yk_wh, "settings", S())
    assert akl.default_daily_limit() == 100_000
    assert yk_wh._threshold() == 5


def test_notify_escalation_signature():
    import inspect

    from app.services import alerts as alerts_svc

    sig = inspect.signature(alerts_svc.notify_escalation)
    assert "task_id" in sig.parameters
    # dual-channel: send_dual defaults used inside
    src = inspect.getsource(alerts_svc.notify_escalation)
    assert "send_dual" in src
    assert "telegram=True" in src
    assert "email=True" in src
