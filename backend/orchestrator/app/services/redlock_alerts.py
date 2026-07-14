"""Конфликт Redlock → Email владельцу сервиса (§12.4.1)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.database import async_session
from app.core.redis import get_redis
from app.models import TaskConflict
from app.services import alerts as alerts_svc

logger = logging.getLogger(__name__)

EVENT = "redlock_conflict"


async def notify_redlock_conflict(
    *,
    task_id: str,
    worker_id: str | None = None,
    reason: str = "lock_not_acquired",
    conflict_with: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Email при невозможности получить блокировку / duplicate (§12.4.1 / §13.3.5)."""
    try:
        redis = await get_redis()
        ck = f"alert:redlock:{task_id}:{reason}"
        if await redis.get(ck):
            return {"ok": True, "skipped": "cooldown"}
        await redis.set(ck, "1", ex=600)
    except Exception:  # noqa: BLE001
        pass

    text = (
        f"🔒 Конфликт Redlock\n"
        f"task_id: {task_id}\n"
        f"worker_id: {worker_id or '—'}\n"
        f"reason: {reason}\n"
        f"conflict_with: {conflict_with or '—'}"
    )
    try:
        async with async_session() as db:
            db.add(
                TaskConflict(
                    task_id=task_id,
                    worker_id=worker_id,
                    reason=reason[:100],
                    details={
                        **(details or {}),
                        "conflict_with": conflict_with,
                    },
                )
            )
            dual = await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT,
                payload={
                    "fingerprint": f"rl:{task_id}:{reason}",
                    "task_id": task_id,
                    "worker_id": worker_id,
                    "reason": reason,
                    "conflict_with": conflict_with,
                },
                subject=f"[3dvektor] Redlock conflict {task_id}",
                telegram=False,
                email=True,
            )
            await db.commit()
            return {"ok": True, "email": dual.get("email")}
    except Exception as exc:  # noqa: BLE001
        logger.warning("redlock alert failed: %s", exc)
        return {"ok": False, "error": str(exc)}
