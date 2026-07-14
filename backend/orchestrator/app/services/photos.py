"""Загрузка 12 ракурсов в MinIO: photos/{task_uuid}/view_XX.jpg."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.minio import minio_service
from app.services import photo_encryption as photo_enc

VIEW_COUNT = 12
VIEW_NAMES = [f"view_{i:02d}.jpg" for i in range(VIEW_COUNT)]
ANGLE_LABELS = [
    "Фронт",
    "Фронт-лево 30°",
    "Лево 60°",
    "Лево 90°",
    "Лево-тыл 120°",
    "Тыл-лево 150°",
    "Тыл",
    "Тыл-право 210°",
    "Право 240°",
    "Право 270°",
    "Право-фронт 300°",
    "Фронт-право 330°",
]


def photos_prefix(task_uuid: str) -> str:
    return f"photos/{task_uuid}/"


def view_key(task_uuid: str, index: int) -> str:
    if index < 0 or index >= VIEW_COUNT:
        raise HTTPException(400, f"Индекс ракурса 0…{VIEW_COUNT - 1}")
    return f"{photos_prefix(task_uuid)}{VIEW_NAMES[index]}"


def prepare_presigned_uploads(
    task_uuid: str,
    *,
    expires: int = 1800,
    encryption_required: bool = False,
) -> dict[str, Any]:
    try:
        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"MinIO недоступен: {exc}") from exc

    bucket = settings.MINIO_BUCKET_PHOTOS
    uploads = []
    for i, name in enumerate(VIEW_NAMES):
        key = f"{photos_prefix(task_uuid)}{name}"
        url = minio_service.generate_presigned_url(bucket, key, expires=expires, method="put_object")
        uploads.append(
            {
                "index": i,
                "filename": name,
                "label": ANGLE_LABELS[i],
                "key": key,
                "upload_url": url,
                "content_type": (
                    "application/octet-stream" if encryption_required else "image/jpeg"
                ),
            }
        )
    return {
        "task_uuid": task_uuid,
        "photos_prefix": photos_prefix(task_uuid),
        "bucket": bucket,
        "expires_in": expires,
        "uploads": uploads,
        "angles": ANGLE_LABELS,
        "encryption_required": encryption_required,
        "encryption_algorithm": photo_enc.ALGORITHM if encryption_required else None,
    }


async def prepare_for_user(
    db: AsyncSession,
    task_uuid: str,
    *,
    company_id: int | None,
    expires: int = 1800,
) -> dict[str, Any]:
    enc = await photo_enc.encryption_enabled_for_company(db, company_id)
    return prepare_presigned_uploads(task_uuid, expires=expires, encryption_required=enc)


def count_uploaded(task_uuid: str) -> int:
    bucket = settings.MINIO_BUCKET_PHOTOS
    prefix = photos_prefix(task_uuid)
    n = 0
    for name in VIEW_NAMES:
        if minio_service.object_exists(bucket, f"{prefix}{name}"):
            n += 1
    return n


def require_all_photos(task_uuid: str) -> None:
    missing = []
    bucket = settings.MINIO_BUCKET_PHOTOS
    prefix = photos_prefix(task_uuid)
    for name in VIEW_NAMES:
        if not minio_service.object_exists(bucket, f"{prefix}{name}"):
            missing.append(name)
    if missing:
        raise HTTPException(400, f"Не хватает фото: {', '.join(missing)}")


def delete_task_photos(task_uuid: str) -> dict[str, Any]:
    """Удалить photos/{task_uuid}/ из MinIO (§3.15.4 TTL)."""
    bucket = settings.MINIO_BUCKET_PHOTOS
    prefix = photos_prefix(task_uuid)
    n = minio_service.delete_prefix(bucket, prefix)
    return {"task_uuid": task_uuid, "bucket": bucket, "prefix": prefix, "deleted": n}


async def upload_files_to_prefix(task_uuid: str, files: list[UploadFile]) -> dict[str, Any]:
    if len(files) != VIEW_COUNT:
        raise HTTPException(400, f"Нужно ровно {VIEW_COUNT} файлов, получено {len(files)}")
    try:
        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"MinIO недоступен: {exc}") from exc

    bucket = settings.MINIO_BUCKET_PHOTOS
    keys: list[str] = []
    for i, f in enumerate(files):
        data = await f.read()
        if not data:
            raise HTTPException(400, f"Пустой файл ракурса {i}")
        key = view_key(task_uuid, i)
        content_type = f.content_type or "image/jpeg"
        minio_service.upload_bytes(bucket, key, data, content_type=content_type)
        keys.append(key)
    return {
        "task_uuid": task_uuid,
        "photos_prefix": photos_prefix(task_uuid),
        "bucket": bucket,
        "keys": keys,
        "count": len(keys),
    }
