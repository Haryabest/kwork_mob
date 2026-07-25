"""Настройки JWT/сессии staff-панели §11.1 — defaults + Redis + DB."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

SESSION_KEYS: dict[str, int] = {
    "staff_jwt_access_expire_minutes": 480,
    "staff_idle_timeout_minutes": 43200,
    "staff_jwt_refresh_expire_days": 30,
}

REDIS_HASH = "staff:session_settings"


def env_defaults() -> dict[str, int]:
    return {
        "staff_jwt_access_expire_minutes": int(
            getattr(settings, "STAFF_JWT_ACCESS_EXPIRE_MINUTES", 480) or 480
        ),
        "staff_idle_timeout_minutes": int(
            getattr(settings, "STAFF_IDLE_TIMEOUT_MINUTES", 43200) or 43200
        ),
        "staff_jwt_refresh_expire_days": int(
            getattr(settings, "JWT_REFRESH_EXPIRE_DAYS", 30) or 30
        ),
    }


def merge_settings(stored: dict | None) -> dict[str, int]:
    base = env_defaults()
    if not stored:
        return base
    out = dict(base)
    for k, default in SESSION_KEYS.items():
        if k not in stored:
            continue
        try:
            v = int(stored[k])
            if k.endswith("_minutes") and v < 5:
                continue
            if k.endswith("_days") and v < 1:
                continue
            if k == "staff_jwt_access_expire_minutes" and not (15 <= v <= 24 * 60):
                continue
            if k == "staff_idle_timeout_minutes" and not (5 <= v <= 30 * 24 * 60):
                continue
            if k == "staff_jwt_refresh_expire_days" and not (1 <= v <= 90):
                continue
            out[k] = v
        except (TypeError, ValueError):
            continue
    return out


async def sync_redis(cfg: dict[str, int]) -> None:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        await redis.hset(REDIS_HASH, mapping={k: str(v) for k, v in cfg.items()})
    except Exception:  # noqa: BLE001
        pass


async def load_settings(db: AsyncSession) -> dict[str, int]:
    from app.services import alerts as alerts_svc

    row = await alerts_svc.get_settings(db)
    thr = row.thresholds if isinstance(row.thresholds, dict) else {}
    nested = thr.get("staff_session")
    stored = nested if isinstance(nested, dict) else {}
    merged = merge_settings(stored)
    await sync_redis(merged)
    return merged


async def save_settings(db: AsyncSession, patch: dict[str, Any]) -> dict[str, int]:
    from app.services import alerts as alerts_svc

    row = await alerts_svc.get_settings(db)
    thr = dict(row.thresholds or {})
    current = dict(thr.get("staff_session") or {})
    for k in SESSION_KEYS:
        if k not in patch:
            continue
        try:
            current[k] = int(patch[k])
        except (TypeError, ValueError):
            continue
    thr["staff_session"] = merge_settings(current)
    row.thresholds = thr
    merged = thr["staff_session"]
    await sync_redis(merged)
    await db.flush()
    return merged


async def get_setting_async(key: str, default: int | None = None) -> int:
    defaults = env_defaults()
    fallback = default if default is not None else defaults.get(key, 0)
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        raw = await redis.hget(REDIS_HASH, key)
        if raw is None:
            return int(fallback)
        return int(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception:  # noqa: BLE001
        return int(fallback)
