"""Алерт битого ZIP / SHA-256 mismatch (§12.4.1 Email)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.database import async_session
from app.services import alerts as alerts_svc

logger = logging.getLogger(__name__)

EVENT = "zip_sha_mismatch"


async def alert_sha_mismatch(
    *,
    task_uuid: str | None = None,
    model_uuid: str | None = None,
    expected: str | None = None,
    actual: str | None = None,
    context: str = "",
) -> dict[str, Any]:
    text = (
        f"📦 Битый ZIP / SHA-256 не совпадает\n"
        f"task_uuid: {task_uuid or '—'}\n"
        f"model_uuid: {model_uuid or '—'}\n"
        f"expected: {(expected or '—')[:16]}…\n"
        f"actual: {(actual or '—')[:16]}…\n"
        f"context: {context[:200]}"
    )
    fp = f"sha:{task_uuid or model_uuid or 'unknown'}:{(expected or '')[:12]}"
    try:
        async with async_session() as db:
            dual = await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT,
                payload={
                    "fingerprint": fp,
                    "task_uuid": task_uuid,
                    "model_uuid": model_uuid,
                    "expected": expected,
                    "actual": actual,
                    "context": context,
                },
                subject="[3dvektor] ZIP SHA-256 mismatch",
                telegram=False,
                email=True,
            )
            await db.commit()
            return {"ok": True, "email": dual.get("email")}
    except Exception as exc:  # noqa: BLE001
        logger.warning("zip sha alert failed: %s", exc)
        return {"ok": False, "error": str(exc)}
