"""Analytics events validation §19.20."""

import pytest
from pydantic import ValidationError

from app.schemas.analytics import AnalyticsEventItem, AnalyticsEventsBody


def test_screen_view_valid():
    item = AnalyticsEventItem(
        event="screen_view",
        ts="2026-07-17T10:00:00Z",
        props={"screen": "queue"},
    )
    assert item.event == "screen_view"


def test_screen_view_missing_screen():
    with pytest.raises(ValidationError):
        AnalyticsEventItem(event="screen_view", ts="2026-07-17T10:00:00Z", props={})


def test_unknown_event_rejected():
    with pytest.raises(ValidationError):
        AnalyticsEventItem(event="tap", ts="2026-07-17T10:00:00Z")


def test_checkout_pay_requires_order_id():
    with pytest.raises(ValidationError):
        AnalyticsEventItem(event="checkout_pay", ts="2026-07-17T10:00:00Z", props={"tier": "small"})


def test_batch_max_length():
    body = AnalyticsEventsBody(
        events=[
            AnalyticsEventItem(
                event="screen_view",
                ts="2026-07-17T10:00:00Z",
                props={"screen": "home"},
            )
        ]
    )
    assert len(body.events) == 1


def test_shoot_step_valid():
    item = AnalyticsEventItem(
        event="shoot_step",
        ts="2026-07-17T10:00:00Z",
        props={"model_uuid": "abc-123", "step": 3},
    )
    assert item.props["step"] == 3


def test_shoot_step_invalid_step():
    with pytest.raises(ValidationError):
        AnalyticsEventItem(
            event="shoot_step",
            ts="2026-07-17T10:00:00Z",
            props={"model_uuid": "abc", "step": 0},
        )


def test_shoot_step_retry_valid():
    item = AnalyticsEventItem(
        event="shoot_step_retry",
        ts="2026-07-17T10:00:00Z",
        props={"model_uuid": "abc-123", "step": 2, "error_type": "blurry"},
    )
    assert item.props["error_type"] == "blurry"


def test_screen_view_banner_id():
    item = AnalyticsEventItem(
        event="screen_view",
        ts="2026-07-17T10:00:00Z",
        props={"screen": "campaign_banner", "banner_id": 42},
    )
    assert item.props["banner_id"] == 42


def test_screen_view_campaign_banner_click():
    item = AnalyticsEventItem(
        event="screen_view",
        ts="2026-07-17T10:00:00Z",
        props={"screen": "campaign_banner_click", "banner_id": 7},
    )
    assert item.props["screen"] == "campaign_banner_click"


def test_screen_view_unknown_screen():
    with pytest.raises(ValidationError):
        AnalyticsEventItem(
            event="screen_view",
            ts="2026-07-17T10:00:00Z",
            props={"screen": "not_a_real_screen"},
        )


def test_screen_view_queue_reconnect_ws():
    item = AnalyticsEventItem(
        event="screen_view",
        ts="2026-07-17T10:00:00Z",
        props={"screen": "queue_reconnect_ws"},
    )
    assert item.props["screen"] == "queue_reconnect_ws"


def test_screen_view_notifications_mark_read():
    item = AnalyticsEventItem(
        event="screen_view",
        ts="2026-07-17T10:00:00Z",
        props={"screen": "notifications_mark_read"},
    )
    assert item.props["screen"] == "notifications_mark_read"
