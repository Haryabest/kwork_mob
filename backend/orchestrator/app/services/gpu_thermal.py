"""GPU thermal alert из heartbeat/metrics (§12.4.1 / §13.4)."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import settings
from app.services import alerts as alerts_svc

logger = logging.getLogger(__name__)

# worker_id → last alert monotonic ts
_last_alert: dict[str, float] = {}


def _threshold() -> float:
    return float(getattr(settings, "GPU_TEMP_ALERT_C", 85) or 85)


def _cooldown() -> float:
    return float(getattr(settings, "GPU_TEMP_ALERT_COOLDOWN_SEC", 600) or 600)


async def maybe_alert_from_metrics(
    worker_id: str,
    gpu: dict[str, Any] | None,
    *,
    task_id: str | None = None,
    force: bool = False,
) -> bool:
    """Если temp ≥ порога — Telegram+email (с cooldown)."""
    if not gpu:
        return False
    try:
        temp = float(gpu.get("gpu_temp") or gpu.get("temp") or gpu.get("temperature") or 0)
    except (TypeError, ValueError):
        return False
    if temp < _threshold() and not force:
        return False
    now = time.monotonic()
    last = _last_alert.get(worker_id, 0.0)
    if not force and (now - last) < _cooldown():
        return False
    _last_alert[worker_id] = now
    try:
        await alerts_svc.notify_gpu_thermal(
            worker_id=worker_id,
            temp_c=temp,
            task_id=task_id,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("gpu thermal alert failed: %s", exc)
        return False
