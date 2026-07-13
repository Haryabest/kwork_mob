"""Подключение к Redis: URL или Sentinel (§4 HA).

Env:
  REDIS_URL=redis://localhost:6379/0
  REDIS_SENTINELS=host1:26379,host2:26379,host3:26379
  REDIS_SENTINEL_MASTER=mymaster
  REDIS_SENTINEL_PASSWORD=
  REDIS_PASSWORD=
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from redis.asyncio.sentinel import Sentinel

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client: aioredis.Redis | None = None


def _parse_sentinels(raw: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            host, port_s = part.rsplit(":", 1)
            out.append((host.strip(), int(port_s)))
        else:
            out.append((part, 26379))
    return out


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is not None:
        return redis_client

    sentinels_raw = (getattr(settings, "REDIS_SENTINELS", None) or "").strip()
    if sentinels_raw:
        nodes = _parse_sentinels(sentinels_raw)
        master = getattr(settings, "REDIS_SENTINEL_MASTER", None) or "mymaster"
        password = getattr(settings, "REDIS_PASSWORD", None) or None
        sentinel_password = getattr(settings, "REDIS_SENTINEL_PASSWORD", None) or password
        sentinel = Sentinel(
            nodes,
            socket_timeout=5.0,
            password=sentinel_password,
        )
        redis_client = sentinel.master_for(
            master,
            redis_class=aioredis.Redis,
            password=password,
            decode_responses=True,
            db=0,
        )
        logger.info("Redis via Sentinel master=%s nodes=%s", master, nodes)
    else:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Redis via URL")
    return redis_client


async def acquire_task_lock(task_id: str, worker_id: str, ttl: int = 60) -> bool:
    """Redlock: SET task:{task_id} processing NX EX ttl."""
    r = await get_redis()
    return await r.set(f"task:{task_id}", worker_id, nx=True, ex=ttl)


async def release_task_lock(task_id: str) -> None:
    r = await get_redis()
    await r.delete(f"task:{task_id}")
