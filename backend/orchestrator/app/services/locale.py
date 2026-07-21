"""Локали §16.1 / §16.4."""

from __future__ import annotations

SUPPORTED_LOCALES = ("ru", "en", "kk", "zh-CN")
DEFAULT_LOCALE = "ru"


def normalize_locale(code: str | None) -> str:
    if not code:
        return DEFAULT_LOCALE
    raw = code.strip().lower().replace("_", "-")
    if raw in ("zh", "zh-cn", "zh-hans"):
        return "zh-CN"
    if raw.startswith("en"):
        return "en"
    if raw.startswith("kk"):
        return "kk"
    if raw == "ru":
        return "ru"
    if raw in SUPPORTED_LOCALES:
        return raw
    return DEFAULT_LOCALE
