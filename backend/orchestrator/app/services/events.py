"""Публикация событий статуса заказа для /ws/queue/{user_id}."""

from __future__ import annotations

import json
from typing import Any

from app.core.redis import get_redis


def user_channel(user_id: int) -> str:
    return f"events:user:{user_id}"


async def publish_user_event(user_id: int, event: dict[str, Any]) -> None:
    """Pub/Sub: клиенты подписаны на канал пользователя."""
    redis = await get_redis()
    await redis.publish(user_channel(user_id), json.dumps(event, ensure_ascii=False))


async def publish_order_status(
    *,
    user_id: int,
    order_id: int,
    task_id: str,
    status: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "order_status",
        "order_id": order_id,
        "task_id": task_id,
        "status": status,
    }
    if extra:
        payload.update(extra)
    await publish_user_event(user_id, payload)
