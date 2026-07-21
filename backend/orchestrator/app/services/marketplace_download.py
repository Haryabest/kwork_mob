"""Marketplace-specific download labels and size limits §7.6 / §6.6.3."""

from __future__ import annotations

OZON_BYTES = 15 * 1024 * 1024
WB_BYTES = 20 * 1024 * 1024
WB_WARN_BYTES = 25 * 1024 * 1024
USDZ_WARN_BYTES = 25 * 1024 * 1024

DOWNLOAD_LABELS: dict[str, dict[str, str]] = {
    "ozon": {
        "glb": "Скачать модель для Ozon (GLB)",
        "usdz": "Скачать модель для Ozon (USDZ)",
    },
    "wb": {
        "glb": "Скачать модель для Wildberries (GLB/Android)",
        "usdz": "Скачать модель для Wildberries (USDZ/iOS)",
    },
}


def normalize_marketplace(value: str | None) -> str:
    mp = (value or "ozon").strip().lower()
    if mp in ("wb", "wildberries", "both"):
        return "wb"
    return "ozon"


def max_bytes(marketplace: str | None, file_format: str = "glb") -> int:
    mp = normalize_marketplace(marketplace)
    if file_format == "usdz":
        return WB_WARN_BYTES if mp == "wb" else OZON_BYTES
    return WB_BYTES if mp == "wb" else OZON_BYTES


def warn_bytes(marketplace: str | None, file_format: str = "glb") -> int:
    mp = normalize_marketplace(marketplace)
    if file_format == "usdz":
        return USDZ_WARN_BYTES
    return WB_WARN_BYTES if mp == "wb" else OZON_BYTES


def download_meta(marketplace: str | None, file_format: str = "glb") -> dict:
    mp = normalize_marketplace(marketplace)
    fmt = file_format if file_format in ("glb", "usdz") else "glb"
    labels = DOWNLOAD_LABELS.get(mp, DOWNLOAD_LABELS["ozon"])
    return {
        "marketplace": mp,
        "button_label": labels.get(fmt) or labels.get("glb"),
        "limit_bytes": max_bytes(mp, fmt),
        "warn_limit_bytes": warn_bytes(mp, fmt),
        "limit_mb": round(max_bytes(mp, fmt) / (1024 * 1024), 1),
    }
