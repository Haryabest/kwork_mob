"""Парсинг User-Agent → device_model / os_version (§11.2.5 / web-seller)."""

from __future__ import annotations

import re


def device_hint_from_ua(ua: str | None) -> tuple[str | None, str | None]:
    """Грубая классификация браузерного UA для segmentation alerts."""
    if not ua or not str(ua).strip():
        return None, None
    raw = str(ua).strip()
    low = raw.lower()

    device = "web"
    if "iphone" in low or "ipad" in low:
        device = "iOS Web"
    elif "android" in low:
        device = "Android Web"
    elif "windows" in low:
        device = "Windows"
    elif "mac os" in low or "macintosh" in low:
        device = "macOS"
    elif "linux" in low:
        device = "Linux"

    os_version = None
    m = re.search(r"\(([^)]+)\)", raw)
    if m:
        os_version = m.group(1).strip()[:64]
    else:
        os_version = raw[:64]

    return device[:64], os_version
