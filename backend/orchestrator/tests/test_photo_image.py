"""Нормализация фото с телефона (HEIC/PNG → JPEG)."""

import io

from PIL import Image

from app.services.photo_image import normalize_photo_bytes


def test_normalize_png_to_jpeg():
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), color=(10, 20, 30)).save(buf, format="PNG")
    out = normalize_photo_bytes(buf.getvalue(), filename="shot.png", content_type="image/png")
    assert out[:2] == b"\xff\xd8"
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG"
