"""Лимиты GLB по маркетплейсу §6.6.3."""

from __future__ import annotations

OZON_BYTES = 15 * 1024 * 1024
WB_BYTES = 20 * 1024 * 1024
WB_WARN_BYTES = 25 * 1024 * 1024


def normalize_marketplace(value: str | None) -> str:
    mp = (value or "ozon").strip().lower()
    if mp in ("wb", "wildberries"):
        return "wb"
    return "ozon"


def max_bytes(marketplace: str | None) -> int:
    return WB_BYTES if normalize_marketplace(marketplace) == "wb" else OZON_BYTES


def warn_bytes(marketplace: str | None) -> int:
    return WB_WARN_BYTES if normalize_marketplace(marketplace) == "wb" else OZON_BYTES


def size_status(size: int, marketplace: str | None) -> dict:
    limit = max_bytes(marketplace)
    warn = warn_bytes(marketplace)
    exceeded = size > limit
    warning = exceeded and size <= warn
    hard = size > warn
    return {
        "marketplace": normalize_marketplace(marketplace),
        "size_bytes": size,
        "limit_bytes": limit,
        "warn_limit_bytes": warn,
        "warning_size_exceeded": exceeded,
        "hard_limit_exceeded": hard,
    }
