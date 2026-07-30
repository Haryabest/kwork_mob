"""Загрузка 12 ракурсов в MinIO: photos/{task_uuid}/view_XX.jpg."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.minio import minio_service
from app.services import photo_encryption as photo_enc
from app.services.photo_image import normalize_photo_bytes

VIEW_COUNT = 12
ALLOWED_PARTIAL_PHOTO_COUNTS = frozenset({1, 3, 5, 6})
VIEW_INDICES_BY_COUNT: dict[int, list[int]] = {
    1: [0],
    3: [0, 4, 8],
    5: [0, 2, 4, 6, 8],
    6: [0, 2, 4, 6, 8, 10],
}
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


async def _read_normalized_jpeg(f: UploadFile) -> bytes:
    raw = await f.read()
    if not raw:
        raise HTTPException(400, "Пустой файл")
    try:
        return normalize_photo_bytes(raw, filename=f.filename, content_type=f.content_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def view_key(task_uuid: str, index: int) -> str:
    if index < 0 or index >= VIEW_COUNT:
        raise HTTPException(400, f"Индекс ракурса 0…{VIEW_COUNT - 1}")
    return f"{photos_prefix(task_uuid)}{VIEW_NAMES[index]}"


def validate_photo_count(photo_count: int) -> int:
    if photo_count not in ALLOWED_PARTIAL_PHOTO_COUNTS and photo_count != VIEW_COUNT:
        raise HTTPException(
            400,
            f"photo_count: 1, 3, 5, 6 или {VIEW_COUNT}, получено {photo_count}",
        )
    return photo_count


def indices_for_photo_count(photo_count: int) -> list[int]:
    validate_photo_count(photo_count)
    if photo_count == VIEW_COUNT:
        return list(range(VIEW_COUNT))
    return VIEW_INDICES_BY_COUNT[photo_count]


def _circular_distance(a: int, b: int, n: int = VIEW_COUNT) -> int:
    d = abs(a - b)
    return min(d, n - d)


def expand_views_to_twelve(task_uuid: str) -> int:
    """Заполнить недостающие ракурсы копией ближайшего загруженного."""
    bucket = settings.MINIO_BUCKET_PHOTOS
    uploaded = {
        i
        for i in range(VIEW_COUNT)
        if minio_service.object_exists(bucket, view_key(task_uuid, i))
    }
    if not uploaded:
        raise HTTPException(400, "Нет загруженных фото для расширения")
    filled = 0
    for i in range(VIEW_COUNT):
        if i in uploaded:
            continue
        nearest = min(uploaded, key=lambda u: (_circular_distance(i, u), u))
        src_key = view_key(task_uuid, nearest)
        dst_key = view_key(task_uuid, i)
        minio_service.client.copy_object(
            CopySource={"Bucket": bucket, "Key": src_key},
            Bucket=bucket,
            Key=dst_key,
        )
        filled += 1
    return filled


def prepare_presigned_uploads(
    task_uuid: str,
    *,
    photo_count: int = VIEW_COUNT,
    expires: int = 1800,
    encryption_required: bool = False,
) -> dict[str, Any]:
    try:
        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"MinIO недоступен: {exc}") from exc

    indices = indices_for_photo_count(photo_count)
    bucket = settings.MINIO_BUCKET_PHOTOS
    uploads = []
    for i in indices:
        name = VIEW_NAMES[i]
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
        "photo_count": photo_count,
        "required_indices": indices,
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
    photo_count: int = VIEW_COUNT,
    expires: int = 1800,
) -> dict[str, Any]:
    enc = await photo_enc.encryption_enabled_for_company(db, company_id)
    return prepare_presigned_uploads(
        task_uuid,
        photo_count=photo_count,
        expires=expires,
        encryption_required=enc,
    )


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


def copy_task_photos(src_uuid: str, dst_uuid: str) -> None:
    """Копия 12 ракурсов для перегенерации §20.4."""
    bucket = settings.MINIO_BUCKET_PHOTOS
    require_all_photos(src_uuid)
    for name in VIEW_NAMES:
        src_key = f"{photos_prefix(src_uuid)}{name}"
        dst_key = f"{photos_prefix(dst_uuid)}{name}"
        minio_service.client.copy_object(
            CopySource={"Bucket": bucket, "Key": src_key},
            Bucket=bucket,
            Key=dst_key,
        )


def copy_front_photo_to_all_views(src_uuid: str, dst_uuid: str) -> None:
    """Перегенерация по 1 фото: view_00 исходника → все 12 ракурсов новой задачи."""
    bucket = settings.MINIO_BUCKET_PHOTOS
    src_key = f"{photos_prefix(src_uuid)}{VIEW_NAMES[0]}"
    if not minio_service.object_exists(bucket, src_key):
        raise HTTPException(400, "Фронтальное фото (view_00) недоступно в исходниках")
    for name in VIEW_NAMES:
        dst_key = f"{photos_prefix(dst_uuid)}{name}"
        minio_service.client.copy_object(
            CopySource={"Bucket": bucket, "Key": src_key},
            Bucket=bucket,
            Key=dst_key,
        )


async def upload_single_replicated(task_uuid: str, file: UploadFile) -> dict[str, Any]:
    """Одно фото → view_00 и копия во все ракурсы (single-image pipeline)."""
    data = await _read_normalized_jpeg(file)
    try:
        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"MinIO недоступен: {exc}") from exc
    bucket = settings.MINIO_BUCKET_PHOTOS
    content_type = "image/jpeg"
    first_key = view_key(task_uuid, 0)
    minio_service.upload_bytes(bucket, first_key, data, content_type=content_type)
    for i in range(1, VIEW_COUNT):
        key = view_key(task_uuid, i)
        minio_service.client.copy_object(
            CopySource={"Bucket": bucket, "Key": first_key},
            Bucket=bucket,
            Key=key,
        )
    return {
        "task_uuid": task_uuid,
        "photos_prefix": photos_prefix(task_uuid),
        "bucket": bucket,
        "replicated": VIEW_COUNT,
    }


def delete_task_photos(task_uuid: str) -> dict[str, Any]:
    """Удалить photos/{task_uuid}/ из MinIO (§3.15.4 TTL)."""
    bucket = settings.MINIO_BUCKET_PHOTOS
    prefix = photos_prefix(task_uuid)
    n = minio_service.delete_prefix(bucket, prefix)
    return {"task_uuid": task_uuid, "bucket": bucket, "prefix": prefix, "deleted": n}


async def upload_at_index(task_uuid: str, view_index: int, file: UploadFile) -> dict[str, Any]:
    if view_index < 0 or view_index >= VIEW_COUNT:
        raise HTTPException(400, f"Индекс ракурса 0…{VIEW_COUNT - 1}")
    data = await _read_normalized_jpeg(file)
    try:
        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"MinIO недоступен: {exc}") from exc
    bucket = settings.MINIO_BUCKET_PHOTOS
    key = view_key(task_uuid, view_index)
    minio_service.upload_bytes(bucket, key, data, content_type="image/jpeg")
    return {
        "task_uuid": task_uuid,
        "index": view_index,
        "key": key,
        "bucket": bucket,
    }


async def upload_files_for_count(
    task_uuid: str,
    files: list[UploadFile],
    *,
    photo_count: int = VIEW_COUNT,
) -> dict[str, Any]:
    validate_photo_count(photo_count)
    if photo_count == 1:
        if len(files) != 1:
            raise HTTPException(400, "Для 1 фото нужен один файл")
        return await upload_single_replicated(task_uuid, files[0])
    if photo_count == VIEW_COUNT:
        return await upload_files_to_prefix(task_uuid, files)

    indices = indices_for_photo_count(photo_count)
    if len(files) != len(indices):
        raise HTTPException(
            400,
            f"Нужно {len(indices)} файлов для режима {photo_count} фото, получено {len(files)}",
        )
    try:
        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"MinIO недоступен: {exc}") from exc

    bucket = settings.MINIO_BUCKET_PHOTOS
    keys: list[str] = []
    for idx, f in zip(indices, files, strict=True):
        data = await _read_normalized_jpeg(f)
        key = view_key(task_uuid, idx)
        minio_service.upload_bytes(bucket, key, data, content_type="image/jpeg")
        keys.append(key)
    expanded = expand_views_to_twelve(task_uuid)
    return {
        "task_uuid": task_uuid,
        "photo_count": photo_count,
        "uploaded_indices": indices,
        "expanded": expanded,
        "photos_prefix": photos_prefix(task_uuid),
        "bucket": bucket,
        "keys": keys,
        "count": len(keys),
    }


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
        data = await _read_normalized_jpeg(f)
        key = view_key(task_uuid, i)
        minio_service.upload_bytes(bucket, key, data, content_type="image/jpeg")
        keys.append(key)
    return {
        "task_uuid": task_uuid,
        "photos_prefix": photos_prefix(task_uuid),
        "bucket": bucket,
        "keys": keys,
        "count": len(keys),
    }
