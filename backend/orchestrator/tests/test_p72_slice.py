"""§13.2 thermal analytics, §13.3 corp limits, §19.2 analytics events."""

from app.schemas.analytics import ALLOWED_EVENTS


def test_analytics_extended_events():
    assert "thermal_warning" in ALLOWED_EVENTS
    assert "checkout_start" in ALLOWED_EVENTS
    assert "app_open" in ALLOWED_EVENTS


def test_corp_limit_error_codes():
    import inspect

    from app.services import company_members as cm

    src = inspect.getsource(cm.enforce_member_limits)
    assert "max_concurrent_orders" in src
    assert "monthly_spending_limit" in src
    assert "photographer_limit_reached" in src


def test_gpu_thermal_service():
    from app.services import gpu_thermal as gt

    assert callable(gt.maybe_alert_from_metrics)
