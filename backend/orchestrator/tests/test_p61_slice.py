"""§8.1 AR tier, §8.2 B2B prices, §8.3 quality retry counter."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services import ar_tier as ar_tier_svc
from app.services import tariffs as tariff_svc
from app.services.task_lifecycle import MAX_QUALITY_GENERATION_ATTEMPTS, handle_quality_gate_failure


def test_ar_tier_small_volume():
    out = ar_tier_svc.suggest_tier(width_m=0.5, height_m=0.5, depth_m=0.5)
    assert out["suggested_tier"] == "small"
    assert out["volume_m3"] == 0.125


def test_ar_tier_large_volume():
    out = ar_tier_svc.suggest_tier(width_m=2.0, height_m=1.0, depth_m=1.0)
    assert out["suggested_tier"] == "large"
    assert out["volume_m3"] == 2.0


def test_apply_company_override_fixed():
    assert tariff_svc.apply_company_override(2990, {"type": "fixed", "value": 2500}) == 2500


def test_apply_company_override_percent():
    assert tariff_svc.apply_company_override(3000, {"type": "percent", "value": 10}) == 2700


@pytest.mark.asyncio
async def test_quality_gate_requeues_before_refund(db, monkeypatch):
    from app.models import Order, TaskQueue

    order = Order(
        id=9100,
        user_id=1,
        task_uuid="qg-retry",
        category="other",
        tier="small",
        status="processing",
        amount=100,
    )
    row = TaskQueue(task_id="qg-retry", order_id=9100, status="processing", worker_id="w1", payload_json={})
    db.add(order)
    db.add(row)
    await db.flush()

    redis = AsyncMock()
    redis.lpush = AsyncMock()
    monkeypatch.setattr("app.services.task_lifecycle.get_redis", AsyncMock(return_value=redis))
    monkeypatch.setattr(
        "app.services.task_lifecycle.publish_order_status",
        AsyncMock(),
    )

    result = await handle_quality_gate_failure(db, "qg-retry", "quality_gate_failed score=0.1 < 0.7")
    assert result["action"] == "requeued"
    assert result["attempt"] == 1
    assert row.status == "queued"
    assert row.payload_json["quality_attempts"] == 1
    redis.lpush.assert_awaited()


@pytest.mark.asyncio
async def test_quality_gate_fails_after_max_attempts(db, monkeypatch):
    from app.models import Order, TaskQueue

    order = Order(
        id=9101,
        user_id=1,
        task_uuid="qg-fail",
        category="other",
        tier="small",
        status="processing",
        amount=0,
    )
    row = TaskQueue(
        task_id="qg-fail",
        order_id=9101,
        status="processing",
        worker_id="w1",
        payload_json={"quality_attempts": MAX_QUALITY_GENERATION_ATTEMPTS - 1},
    )
    db.add(order)
    db.add(row)
    await db.flush()

    monkeypatch.setattr("app.services.task_lifecycle.get_redis", AsyncMock())
    monkeypatch.setattr("app.services.task_lifecycle.publish_order_status", AsyncMock())
    monkeypatch.setattr(
        "app.services.company_webhooks.emit",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.task_lifecycle._notify_order_user_push",
        AsyncMock(),
    )

    result = await handle_quality_gate_failure(db, "qg-fail", "quality_gate_failed score=0.1 < 0.7")
    assert result["action"] == "failed"
    assert result["attempt"] == MAX_QUALITY_GENERATION_ATTEMPTS
    assert order.status == "failed"
