"""Целевой polycount по категории §6.3.2."""

from __future__ import annotations

# середина диапазонов ТЗ §6.3.2
CATEGORY_FACES: dict[str, int] = {
    "electronics": 175_000,
    "furniture": 175_000,
    "clothing": 125_000,
    "shoes": 125_000,
    "toys": 125_000,
    "decor": 150_000,
    "other": 150_000,
    "adult": 125_000,
}

PREMIUM_TIER_LARGE = 225_000  # §6.3.2 корп. premium / large tier


def target_faces(category: str | None, *, tier: str | None = None) -> int:
    if (tier or "").lower() == "large":
        return PREMIUM_TIER_LARGE
    return CATEGORY_FACES.get((category or "other").lower(), 150_000)
