"""Очередь задач: Redis List + PostgreSQL dual-write (§4.2)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models import TaskQueue


class QueueService:
    QUEUE_NORMAL = "queue:normal"
    QUEUE_HIGH = "queue:high"

    def _key(self, priority: str) -> str:
        return self.QUEUE_HIGH if priority == "high" else self.QUEUE_NORMAL

    async def enqueue(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        order_id: int,
        company_id: int | None,
        payload: dict[str, Any],
        priority: str = "normal",
    ) -> TaskQueue:
        """Dual-write: INSERT task_queue + RPUSH Redis."""
        existing = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
        if existing:
            if existing.status in ("queued", "failed"):
                existing.status = "queued"
                existing.payload_json = payload
                existing.priority = priority
                await db.flush()
                redis = await get_redis()
                item = json.dumps(
                    {"task_id": task_id, "order_id": order_id, "payload": payload},
                    ensure_ascii=False,
                )
                # не дублировать, если уже в списке
                known = False
                for key in (self.QUEUE_HIGH, self.QUEUE_NORMAL):
                    for raw in await redis.lrange(key, 0, -1):
                        try:
                            if json.loads(raw).get("task_id") == task_id:
                                known = True
                                break
                        except json.JSONDecodeError:
                            continue
                    if known:
                        break
                if not known:
                    await redis.rpush(self._key(priority), item)
            return existing

        row = TaskQueue(
            task_id=task_id,
            order_id=order_id,
            company_id=company_id,
            priority=priority,
            payload_json=payload,
            status="queued",
        )
        db.add(row)
        await db.flush()

        redis = await get_redis()
        await redis.rpush(
            self._key(priority),
            json.dumps({"task_id": task_id, "order_id": order_id, "payload": payload}, ensure_ascii=False),
        )
        return row

    async def dequeue(self) -> dict[str, Any] | None:
        """LPOP high → normal. Возвращает {task_id, order_id, payload}."""
        redis = await get_redis()
        for key in (self.QUEUE_HIGH, self.QUEUE_NORMAL):
            raw = await redis.lpop(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not data.get("task_id"):
                continue
            return data
        return None

    async def remove_from_redis(self, task_id: str) -> int:
        """Удалить все вхождения task_id из queue:high/normal."""
        redis = await get_redis()
        removed = 0
        for key in (self.QUEUE_HIGH, self.QUEUE_NORMAL):
            items = await redis.lrange(key, 0, -1)
            keep: list[str] = []
            for raw in items:
                try:
                    if json.loads(raw).get("task_id") == task_id:
                        removed += 1
                        continue
                except json.JSONDecodeError:
                    pass
                keep.append(raw)
            await redis.delete(key)
            if keep:
                await redis.rpush(key, *keep)
        return removed

    async def sync_from_postgres(self, db: AsyncSession) -> int:
        """Восстановить в Redis задачи со статусом queued, которых нет в списках."""
        redis = await get_redis()
        restored = 0
        for priority, key in (("normal", self.QUEUE_NORMAL), ("high", self.QUEUE_HIGH)):
            raw_items = await redis.lrange(key, 0, -1)
            known = set()
            for raw in raw_items:
                try:
                    known.add(json.loads(raw).get("task_id"))
                except json.JSONDecodeError:
                    continue

            rows = (
                await db.scalars(
                    select(TaskQueue).where(
                        TaskQueue.status == "queued",
                        TaskQueue.priority == priority,
                    )
                )
            ).all()
            for row in rows:
                if row.task_id in known:
                    continue
                await redis.rpush(
                    key,
                    json.dumps(
                        {
                            "task_id": row.task_id,
                            "order_id": row.order_id,
                            "payload": row.payload_json or {},
                        },
                        ensure_ascii=False,
                    ),
                )
                restored += 1
        return restored

    async def queue_lengths(self) -> dict[str, int]:
        redis = await get_redis()
        return {
            "normal": int(await redis.llen(self.QUEUE_NORMAL)),
            "high": int(await redis.llen(self.QUEUE_HIGH)),
        }

    async def estimate_wait_time(self, position: int) -> int:
        """EWT в секундах (~3 мин на задачу)."""
        return max(position, 1) * 180

    async def position_for_task(self, task_id: str) -> int | None:
        redis = await get_redis()
        pos = 0
        for key in (self.QUEUE_HIGH, self.QUEUE_NORMAL):
            items = await redis.lrange(key, 0, -1)
            for raw in items:
                pos += 1
                try:
                    if json.loads(raw).get("task_id") == task_id:
                        return pos
                except json.JSONDecodeError:
                    continue
        return None


queue_service = QueueService()
