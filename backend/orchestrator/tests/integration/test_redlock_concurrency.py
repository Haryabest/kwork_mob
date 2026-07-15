"""Redlock: только один воркер захватывает задачу (§4 / §5.2).

Критический путь: при двух воркерах, одновременно берущих одну задачу,
захват должен получить ровно один. Проверяем на живом Redis (SET NX EX).
"""

import pytest

from app.core.redis import acquire_task_lock, release_task_lock

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_only_one_worker_acquires_lock(redis_client):
    task = "task-integration-lock-1"

    first = await acquire_task_lock(task, "worker-A", ttl=30)
    second = await acquire_task_lock(task, "worker-B", ttl=30)

    assert first is True
    assert not second  # None/False — повторный захват недопустим

    # После release задачу может взять другой воркер.
    await release_task_lock(task)
    third = await acquire_task_lock(task, "worker-C", ttl=30)
    assert third is True
    await release_task_lock(task)


async def test_lock_ttl_expires(redis_client):
    task = "task-integration-lock-ttl"
    assert await acquire_task_lock(task, "worker-A", ttl=1) is True
    # Пока TTL активен — второй захват невозможен.
    assert not await acquire_task_lock(task, "worker-B", ttl=1)
    ttl = await redis_client.ttl(f"task:{task}")
    assert 0 < ttl <= 1
    await release_task_lock(task)
