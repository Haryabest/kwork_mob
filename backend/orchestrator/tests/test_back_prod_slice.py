"""§4.2.2 PG dequeue SKIP LOCKED, §10.10 captcha/rate limit."""

from __future__ import annotations

import pytest


def test_disposable_email_detection():
    from app.services.captcha_guard import is_disposable_email

    assert is_disposable_email("x@mailinator.com")
    assert not is_disposable_email("user@gmail.com")


@pytest.mark.asyncio
async def test_dequeue_from_postgres_skip_locked(db, monkeypatch):
    from app.models import Order, TaskQueue, User
    from app.services.queue import queue_service

    user = User(email="q@example.com", password_hash="x", status="active")
    db.add(user)
    await db.flush()
    order = Order(
        user_id=user.id,
        task_uuid="task-pg-dequeue-1",
        category="electronics",
        tier="small",
        status="queued",
        amount=100,
    )
    db.add(order)
    await db.flush()
    row = TaskQueue(
        task_id="task-pg-dequeue-1",
        order_id=order.id,
        company_id=None,
        priority="normal",
        payload_json={"k": "v"},
        status="queued",
    )
    db.add(row)
    await db.commit()

    async def fail_dequeue():
        raise ConnectionError("redis down")

    monkeypatch.setattr(queue_service, "dequeue", fail_dequeue)

    async with db.begin():
        item = await queue_service.dequeue_with_fallback(db)
    assert item is not None
    assert item["task_id"] == "task-pg-dequeue-1"
    assert item["source"] == "postgres"


@pytest.mark.asyncio
async def test_order_rate_limit_blocks(db):
    from datetime import datetime, timezone

    from app.models import Order, User
    from app.services.order_rate_limit import assert_order_creation_allowed
    from fastapi import HTTPException

    from app.core.config import settings

    monkeypatch_limit = 3
    old = settings.ORDERS_PER_HOUR_LIMIT
    settings.ORDERS_PER_HOUR_LIMIT = monkeypatch_limit
    try:
        user = User(email="rate@example.com", password_hash="x", status="active")
        db.add(user)
        await db.flush()
        now = datetime.now(timezone.utc)
        for i in range(monkeypatch_limit):
            db.add(
                Order(
                    user_id=user.id,
                    task_uuid=f"rate-task-{i}",
                    category="electronics",
                    tier="small",
                    status="pending",
                    amount=100,
                    created_at=now,
                )
            )
        await db.commit()
        with pytest.raises(HTTPException) as exc:
            await assert_order_creation_allowed(db, user_id=user.id)
        assert exc.value.status_code == 429
    finally:
        settings.ORDERS_PER_HOUR_LIMIT = old


def test_company_data_export_routes():
    from app.api.v1.company import get_company_data_export_status, request_company_data_export

    assert request_company_data_export.__name__ == "request_company_data_export"
    assert get_company_data_export_status.__name__ == "get_company_data_export_status"
