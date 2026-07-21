"""Публикация событий статуса заказа для /ws/queue/{user_id}."""

from __future__ import annotations

import json
from typing import Any

from app.core.redis import get_redis


def user_channel(user_id: int) -> str:
    return f"events:user:{user_id}"


def admin_dashboard_channel() -> str:
    return "events:admin:dashboard"


async def publish_user_event(user_id: int, event: dict[str, Any]) -> None:
    """Pub/Sub: клиенты подписаны на канал пользователя."""
    redis = await get_redis()
    await redis.publish(user_channel(user_id), json.dumps(event, ensure_ascii=False))


async def publish_admin_dashboard(event: dict[str, Any]) -> None:
    """Pub/Sub: web-admin dashboard live updates §11.15."""
    redis = await get_redis()
    await redis.publish(admin_dashboard_channel(), json.dumps(event, ensure_ascii=False))


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
    try:
        await publish_admin_dashboard(
            {
                "type": "dashboard_refresh",
                "reason": "order_status",
                "order_id": order_id,
                "status": status,
            }
        )
    except Exception:  # noqa: BLE001
        pass
