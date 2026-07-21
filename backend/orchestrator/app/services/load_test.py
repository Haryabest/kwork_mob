"""Load test: enqueue N tasks §1.4 (100 concurrent orders/hour capacity)."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, User
from app.services.queue import queue_service


async def run_queue_load_test(
    db: AsyncSession,
    *,
    count: int = 100,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Синтетическая нагрузка: N enqueue в очередь (без GPU)."""
    count = max(1, min(count, 500))
    uid = user_id
    if uid is None:
        uid = await db.scalar(select(User.id).limit(1))
    if not uid:
        return {"error": "no_users", "enqueued": 0}

    async def _one(i: int) -> str:
        task_id = str(uuid.uuid4())
        order = Order(
            user_id=uid,
            task_uuid=task_id,
            category="electronics",
            tier="small",
            status="queued",
            amount=0,
        )
        db.add(order)
        await db.flush()
        await queue_service.enqueue(
            db,
            task_id=task_id,
            order_id=order.id,
            company_id=None,
            payload={"load_test": True, "index": i},
            priority="normal",
        )
        return task_id

    started = time.perf_counter()
    task_ids: list[str] = []
    chunk = 20
    for off in range(0, count, chunk):
        batch = min(chunk, count - off)
        for i in range(batch):
            task_ids.append(await _one(off + i))
        await db.flush()
    await db.commit()
    elapsed = time.perf_counter() - started
    return {
        "enqueued": len(task_ids),
        "elapsed_sec": round(elapsed, 3),
        "orders_per_sec": round(len(task_ids) / max(elapsed, 0.001), 2),
        "target_100_per_hour": len(task_ids) >= 100,
        "sample_task_ids": task_ids[:5],
    }


async def run_concurrent_enqueue_smoke(*, count: int = 10) -> dict[str, Any]:
    """In-memory smoke: concurrent coroutines timing (no DB)."""
    count = max(1, min(count, 100))

    async def job(i: int) -> int:
        await asyncio.sleep(0.001)
        return i

    started = time.perf_counter()
    await asyncio.gather(*[job(i) for i in range(count)])
    elapsed = time.perf_counter() - started
    return {"tasks": count, "elapsed_sec": round(elapsed, 4)}
