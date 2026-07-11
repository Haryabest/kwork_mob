"""Подключение к Redis и Redlock."""

import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def acquire_task_lock(task_id: str, worker_id: str, ttl: int = 60) -> bool:
    """Redlock: SET task:{task_id} processing NX EX ttl."""
    r = await get_redis()
    return await r.set(f"task:{task_id}", worker_id, nx=True, ex=ttl)


async def release_task_lock(task_id: str) -> None:
    r = await get_redis()
    await r.delete(f"task:{task_id}")
