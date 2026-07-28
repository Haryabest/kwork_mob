"""Нормализация загружаемых фото (iPhone HEIC, PNG, WebP → JPEG для MinIO/worker)."""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

MAX_EDGE = 4096
JPEG_QUALITY = 90

_heif_registered = False


def _register_heif() -> None:
    global _heif_registered
    if _heif_registered:
        return
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    _heif_registered = True


def normalize_photo_bytes(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> bytes:
    """Любой растр → JPEG (view_XX.jpg в MinIO)."""
    if not data:
        raise ValueError("Пустой файл")
    _register_heif()
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > MAX_EDGE:
            img.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buf.getvalue()
    except Exception as exc:  # noqa: BLE001
        hint = filename or content_type or "image"
        logger.warning("photo normalize failed (%s): %s", hint, exc)
        raise ValueError(
            "Не удалось прочитать изображение. Загрузите JPG/PNG или сделайте снимок через камеру ещё раз."
        ) from exc
