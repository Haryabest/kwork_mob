"""Проверка DWT/HMAC водяного знака (§5.12 / §11)."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
from typing import Any

from app.core.config import settings


def verify_hmac_payload(user_id: int, company_id: int | None, order_id: int, timestamp: int, digest: str) -> bool:
    secret = settings.WATERMARK_HMAC_SECRET
    payload = f"{user_id}:{company_id or 0}:{order_id}:{timestamp}"
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, digest)


def verify_glb_bytes(data: bytes) -> dict[str, Any]:
    """Извлечь extras.hmac и проверить подпись. DWT — best-effort."""
    try:
        from pygltflib import GLTF2
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"pygltflib: {exc}"}

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "m.glb"
        path.write_bytes(data)
        try:
            gltf = GLTF2().load(str(path))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"glb parse: {exc}"}

    extras = gltf.extras if isinstance(gltf.extras, dict) else {}
    if not extras and getattr(gltf, "extras", None):
        try:
            extras = dict(gltf.extras)
        except Exception:  # noqa: BLE001
            extras = {}

    digest = extras.get("hmac")
    if not digest:
        return {"ok": False, "error": "hmac missing in extras", "extras": extras}

    user_id = int(extras.get("user_id") or 0)
    company_id = extras.get("company_id")
    order_id = int(extras.get("order_id") or 0)
    ts = int(extras.get("timestamp") or 0)
    valid = verify_hmac_payload(user_id, company_id, order_id, ts, str(digest))
    return {
        "ok": valid,
        "hmac_valid": valid,
        "user_id": user_id,
        "company_id": company_id,
        "order_id": order_id,
        "timestamp": ts,
        "watermark": extras.get("watermark"),
        "extras": extras,
    }
