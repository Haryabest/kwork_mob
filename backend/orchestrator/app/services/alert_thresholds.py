"""Пороги алертов §12.4.1 — defaults + Redis sync + DB."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

# ключи UI / Redis ↔ env defaults
THRESHOLD_KEYS: dict[str, Any] = {
    "queue_alert_length": 20,
    "all_busy_alert_minutes": 5,
    "worker_offline_alert_seconds": 30,
    "gpu_temp_alert_c": 85,
    "yookassa_error_streak": 5,
    "yookassa_webhook_fail_streak": 5,
    "company_webhook_fail_streak": 3,
    "company_low_balance_rub": 5000,
    "company_suspicious_orders_10m": 50,
    "company_suspicious_window_min": 10,
    "shoot_link_mass_limit_per_hour": 100,
    "shoot_link_mass_block_hours": 1,
    "publication_conversion_alert_ratio": 0.30,
    "fallback_segmentation_alert_ratio": 0.15,
    "api_key_default_daily_limit": 100_000,
    # Storage cluster §11.16.5 / §12.4.1
    "storage_disk_free_min_percent": 10,
    "storage_ssd_wear_min_percent": 15,
    "storage_temp_alert_c": 75,
    "storage_pg_lag_alert_bytes": 1_073_741_824,  # 1 GiB
    "storage_minio_repl_fail_minutes": 5,
    "storage_node_offline_seconds": 60,
    "storage_write_stale_minutes": 10,
    "storage_write_freeze_minutes": 5,
    # Cloud GPU budget §11.3.3 / soft-launch
    "cloud_monthly_budget_rub": 0,
    "cloud_daily_budget_rub": 0,
    "cloud_burn_alert_rub_per_hour": 500,
    "analytics_ch_sync_pending_max": 1000,
    "gateway_ip_rate_limit_per_min": 1000,
    "gateway_jwt_rate_limit_per_min": 100,
    "gateway_rate_block_sec": 300,
    "cloud_idle_stop_interval_min": 5,
}

REDIS_HASH = "alerts:thresholds"


def env_defaults() -> dict[str, Any]:
    return {
        "queue_alert_length": int(getattr(settings, "QUEUE_ALERT_LENGTH", 20) or 20),
        "all_busy_alert_minutes": int(getattr(settings, "ALL_BUSY_ALERT_MINUTES", 5) or 5),
        "worker_offline_alert_seconds": int(getattr(settings, "WORKER_OFFLINE_ALERT_SECONDS", 30) or 30),
        "gpu_temp_alert_c": int(getattr(settings, "GPU_TEMP_ALERT_C", 85) or 85),
        "yookassa_error_streak": int(getattr(settings, "YOOKASSA_ERROR_STREAK_ALERT", 5) or 5),
        "yookassa_webhook_fail_streak": int(getattr(settings, "YOOKASSA_WEBHOOK_FAIL_STREAK", 5) or 5),
        "company_webhook_fail_streak": int(getattr(settings, "COMPANY_WEBHOOK_FAIL_STREAK", 3) or 3),
        "company_low_balance_rub": int(getattr(settings, "COMPANY_LOW_BALANCE_ALERT_RUB", 5000) or 5000),
        "company_suspicious_orders_10m": int(getattr(settings, "COMPANY_SUSPICIOUS_ORDERS_10M", 50) or 50),
        "company_suspicious_window_min": int(getattr(settings, "COMPANY_SUSPICIOUS_WINDOW_MIN", 10) or 10),
        "shoot_link_mass_limit_per_hour": int(getattr(settings, "SHOOT_LINK_MASS_LIMIT_PER_HOUR", 100) or 100),
        "shoot_link_mass_block_hours": int(getattr(settings, "SHOOT_LINK_MASS_BLOCK_HOURS", 1) or 1),
        "publication_conversion_alert_ratio": float(
            getattr(settings, "PUBLICATION_CONVERSION_ALERT_RATIO", 0.30) or 0.30
        ),
        "fallback_segmentation_alert_ratio": float(
            getattr(settings, "FALLBACK_SEGMENTATION_ALERT_RATIO", 0.15) or 0.15
        ),
        "api_key_default_daily_limit": int(getattr(settings, "API_KEY_DEFAULT_DAILY_LIMIT", 100_000) or 100_000),
        "storage_disk_free_min_percent": int(getattr(settings, "STORAGE_DISK_FREE_MIN_PERCENT", 10) or 10),
        "storage_ssd_wear_min_percent": int(getattr(settings, "STORAGE_SSD_WEAR_MIN_PERCENT", 15) or 15),
        "storage_temp_alert_c": int(getattr(settings, "STORAGE_TEMP_ALERT_C", 75) or 75),
        "storage_pg_lag_alert_bytes": int(
            getattr(settings, "STORAGE_PG_LAG_ALERT_BYTES", 1_073_741_824) or 1_073_741_824
        ),
        "storage_minio_repl_fail_minutes": int(getattr(settings, "STORAGE_MINIO_REPL_FAIL_MINUTES", 5) or 5),
        "storage_node_offline_seconds": int(getattr(settings, "STORAGE_NODE_OFFLINE_SECONDS", 60) or 60),
        "storage_write_stale_minutes": int(getattr(settings, "STORAGE_WRITE_STALE_MINUTES", 10) or 10),
        "storage_write_freeze_minutes": int(getattr(settings, "STORAGE_WRITE_FREEZE_MINUTES", 5) or 5),
        "cloud_monthly_budget_rub": int(getattr(settings, "CLOUD_MONTHLY_BUDGET_RUB", 0) or 0),
        "cloud_daily_budget_rub": int(getattr(settings, "CLOUD_DAILY_BUDGET_RUB", 0) or 0),
        "cloud_burn_alert_rub_per_hour": int(getattr(settings, "CLOUD_BURN_ALERT_RUB_PER_HOUR", 500) or 500),
        "analytics_ch_sync_pending_max": int(
            getattr(settings, "ANALYTICS_CH_SYNC_PENDING_MAX", 1000) or 1000
        ),
        "gateway_ip_rate_limit_per_min": int(
            getattr(settings, "GATEWAY_IP_RATE_LIMIT_PER_MIN", 1000) or 1000
        ),
        "gateway_jwt_rate_limit_per_min": int(
            getattr(settings, "GATEWAY_JWT_RATE_LIMIT_PER_MIN", 100) or 100
        ),
        "gateway_rate_block_sec": int(getattr(settings, "GATEWAY_RATE_BLOCK_SEC", 300) or 300),
        "cloud_idle_stop_interval_min": int(
            getattr(settings, "CLOUD_IDLE_STOP_INTERVAL_MIN", 5) or 5
        ),
    }


def merge_thresholds(stored: dict | None) -> dict[str, Any]:
    base = env_defaults()
    if not stored:
        return base
    out = dict(base)
    for k, v in stored.items():
        if k not in THRESHOLD_KEYS:
            continue
        try:
            typ = type(THRESHOLD_KEYS[k])
            out[k] = typ(v)
        except (TypeError, ValueError):
            continue
    return out


async def sync_thresholds_redis(thresholds: dict[str, Any]) -> None:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        mapping = {k: str(v) for k, v in thresholds.items()}
        if mapping:
            await redis.hset(REDIS_HASH, mapping=mapping)
    except Exception:  # noqa: BLE001
        pass


async def load_thresholds(db: AsyncSession) -> dict[str, Any]:
    from app.services import alerts as alerts_svc

    cfg = await alerts_svc.get_settings(db)
    merged = merge_thresholds(cfg.thresholds if isinstance(cfg.thresholds, dict) else {})
    await sync_thresholds_redis(merged)
    return merged


async def save_thresholds(db: AsyncSession, patch: dict[str, Any]) -> dict[str, Any]:
    from app.services import alerts as alerts_svc

    cfg = await alerts_svc.get_settings(db)
    current = dict(cfg.thresholds or {})
    for k, v in patch.items():
        if k not in THRESHOLD_KEYS:
            continue
        try:
            typ = type(THRESHOLD_KEYS[k])
            current[k] = typ(v)
        except (TypeError, ValueError):
            continue
    cfg.thresholds = current
    merged = merge_thresholds(current)
    await sync_thresholds_redis(merged)
    await db.flush()
    return merged


def threshold_sync(key: str, default: Any) -> Any:
    """Синхронное чтение порога из Redis (Celery / sync helpers)."""
    try:
        import asyncio

        from app.core.redis import get_redis

        async def _get():
            redis = await get_redis()
            raw = await redis.hget(REDIS_HASH, key)
            return raw

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # нельзя block — fallback env
            return default
        raw = asyncio.run(_get())
        if raw is None:
            return default
        typ = type(default)
        return typ(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception:  # noqa: BLE001
        return default


async def threshold_async(key: str, default: Any) -> Any:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        raw = await redis.hget(REDIS_HASH, key)
        if raw is None:
            return default
        typ = type(default)
        return typ(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception:  # noqa: BLE001
        return default
