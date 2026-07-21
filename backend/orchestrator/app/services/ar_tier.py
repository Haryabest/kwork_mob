"""AR volume → tariff suggestion §8.3."""

from __future__ import annotations

VOLUME_THRESHOLD_M3 = 1.0


def volume_m3(*, width_m: float, height_m: float, depth_m: float) -> float:
    return max(0.0, width_m) * max(0.0, height_m) * max(0.0, depth_m)


def suggest_tier(*, width_m: float, height_m: float, depth_m: float) -> dict:
    vol = volume_m3(width_m=width_m, height_m=height_m, depth_m=depth_m)
    suggested = "small" if vol <= VOLUME_THRESHOLD_M3 else "large"
    return {
        "volume_m3": round(vol, 6),
        "suggested_tier": suggested,
        "threshold_m3": VOLUME_THRESHOLD_M3,
        "dimensions_m": {
            "width": width_m,
            "height": height_m,
            "depth": depth_m,
        },
    }


def suggest_from_calibration(scale_calibration: dict | None) -> dict | None:
    if not isinstance(scale_calibration, dict):
        return None
    try:
        w = float(scale_calibration.get("width") or scale_calibration.get("w") or 0)
        h = float(scale_calibration.get("height") or scale_calibration.get("h") or 0)
        d = float(scale_calibration.get("depth") or scale_calibration.get("d") or 0)
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0 or d <= 0:
        return None
    return suggest_tier(width_m=w, height_m=h, depth_m=d)
