"""§13.1 quality gate e2e — requeue then refund."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.task_lifecycle import MAX_QUALITY_GENERATION_ATTEMPTS, handle_quality_gate_failure


@pytest.mark.asyncio
async def test_quality_gate_e2e_requeue_then_fail(db, monkeypatch):
    from app.models import Order, TaskQueue

    order = Order(
        id=9200,
        user_id=1,
        task_uuid="qg-e2e",
        category="other",
        tier="small",
        status="processing",
        amount=500,
    )
    row = TaskQueue(
        task_id="qg-e2e",
        order_id=9200,
        status="processing",
        worker_id="w1",
        priority="normal",
        payload_json={},
    )
    db.add(order)
    db.add(row)
    await db.flush()

    redis = AsyncMock()
    redis.lpush = AsyncMock()
    monkeypatch.setattr("app.services.task_lifecycle.get_redis", AsyncMock(return_value=redis))
    monkeypatch.setattr("app.services.task_lifecycle.publish_order_status", AsyncMock())
    monkeypatch.setattr("app.services.company_webhooks.emit", AsyncMock())
    monkeypatch.setattr("app.services.task_lifecycle._notify_order_user_push", AsyncMock())

    first = await handle_quality_gate_failure(db, "qg-e2e", "quality_gate_failed score=0.1 < 0.7")
    assert first["action"] == "requeued"
    assert first["attempt"] == 1

    row.payload_json = {"quality_attempts": MAX_QUALITY_GENERATION_ATTEMPTS - 1}
    await db.flush()
    final = await handle_quality_gate_failure(db, "qg-e2e", "quality_gate_failed score=0.1 < 0.7")
    assert final["action"] == "failed"
    assert final["attempt"] == MAX_QUALITY_GENERATION_ATTEMPTS
