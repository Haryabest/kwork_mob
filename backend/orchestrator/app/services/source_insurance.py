"""Страхующая копия source.zip в MinIO backups §9.1.2 / 5.4."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services import photos as photos_service
from app.services.minio import minio_service
from app.services.model_storage import ttl_days


def _copy_object(
    *,
    src_bucket: str,
    src_key: str,
    dest_bucket: str,
    dest_key: str,
    content_type: str,
) -> None:
    data = minio_service.download_bytes(src_bucket, src_key)
    minio_service.upload_bytes(dest_bucket, dest_key, data, content_type=content_type)


def store_insurance_copy(
    *,
    task_uuid: str,
    user_id: int,
    company_id: int | None,
    zip_key: str,
    meta_key: str | None = None,
) -> dict[str, Any]:
    """Копия photos ZIP → backups/{user_id}/{task_uuid}/ (+ company path)."""
    photos_bucket = settings.MINIO_BUCKET_PHOTOS
    backups_bucket = settings.MINIO_BUCKET_BACKUPS
    meta_src = meta_key or f"{photos_service.photos_prefix(task_uuid)}metadata.json"
    keys: list[str] = []

    def _store(prefix: str) -> None:
        zip_dest = f"{prefix}/source.zip"
        meta_dest = f"{prefix}/metadata.json"
        _copy_object(
            src_bucket=photos_bucket,
            src_key=zip_key,
            dest_bucket=backups_bucket,
            dest_key=zip_dest,
            content_type="application/zip",
        )
        keys.append(zip_dest)
        if minio_service.object_exists(photos_bucket, meta_src):
            _copy_object(
                src_bucket=photos_bucket,
                src_key=meta_src,
                dest_bucket=backups_bucket,
                dest_key=meta_dest,
                content_type="application/json",
            )

    _store(f"backups/{user_id}/{task_uuid}")
    if company_id:
        _store(f"backups/company_{company_id}/{task_uuid}")

    return {
        "ok": True,
        "keys": keys,
        "ttl_days": ttl_days(),
        "task_uuid": task_uuid,
    }
