"""Режимы загрузки 1/3/5/6 фото для нового заказа."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import photos as photos_svc


def test_indices_for_photo_count():
    assert photos_svc.indices_for_photo_count(1) == [0]
    assert photos_svc.indices_for_photo_count(3) == [0, 3, 9]
    assert photos_svc.indices_for_photo_count(5) == [0, 2, 4, 6, 8]
    assert photos_svc.indices_for_photo_count(6) == [0, 2, 4, 6, 8, 10]
    assert photos_svc.indices_for_photo_count(12) == list(range(12))


def test_validate_photo_count_rejects_unknown():
    with pytest.raises(HTTPException) as exc:
        photos_svc.validate_photo_count(2)
    assert exc.value.status_code == 400


def test_circular_distance():
    assert photos_svc._circular_distance(0, 11) == 1
    assert photos_svc._circular_distance(0, 6) == 6


def test_expand_views_to_twelve_fills_missing():
    exists = {0, 3, 6}

    def fake_exists(_bucket, key):
        for i in exists:
            if key.endswith(f"view_{i:02d}.jpg"):
                return True
        return False

    with patch.object(photos_svc.minio_service, "object_exists", side_effect=fake_exists), patch.object(
        photos_svc.minio_service.client, "copy_object"
    ) as copy_obj:
        filled = photos_svc.expand_views_to_twelve("task-1")
    assert filled == 9
    assert copy_obj.call_count == 9


def _jpeg_bytes(color: tuple[int, int, int]) -> bytes:
  import io

  from PIL import Image

  buf = io.BytesIO()
  Image.new("RGB", (8, 8), color).save(buf, format="JPEG")
  return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_files_for_count_partial_expands():
  file_a = MagicMock()
  file_a.read = AsyncMock(return_value=_jpeg_bytes((255, 0, 0)))
  file_a.filename = "a.jpg"
  file_a.content_type = "image/jpeg"
  file_b = MagicMock()
  file_b.read = AsyncMock(return_value=_jpeg_bytes((0, 255, 0)))
  file_b.filename = "b.jpg"
  file_b.content_type = "image/jpeg"
  file_c = MagicMock()
  file_c.read = AsyncMock(return_value=_jpeg_bytes((0, 0, 255)))
  file_c.filename = "c.jpg"
  file_c.content_type = "image/jpeg"

  with patch.object(photos_svc.minio_service, "ensure_buckets"), patch.object(
    photos_svc.minio_service, "upload_bytes"
  ) as upload_bytes, patch.object(
    photos_svc, "expand_views_to_twelve", return_value=9
  ) as expand:
    out = await photos_svc.upload_files_for_count(
      "task-1",
      [file_a, file_b, file_c],
      photo_count=3,
    )
  assert out["photo_count"] == 3
  assert out["uploaded_indices"] == [0, 3, 9]
  assert upload_bytes.call_count == 3
  expand.assert_called_once_with("task-1")
