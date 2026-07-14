"""Восстановление исходников из MinIO §9.1.3."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog, Model3D, Order, User
from app.services import access_log as access_svc
from app.services import photos as photos_service
from app.services.minio import minio_service


def _candidate_keys(model: Model3D, order: Order | None) -> list[tuple[str, str]]:
    """(bucket, key) кандидаты source.zip."""
    uuid = model.uuid
    user_id = model.user_id
    company_id = model.company_id
    task = order.task_uuid if order else None
    out: list[tuple[str, str]] = []
    backups = settings.MINIO_BUCKET_BACKUPS
    photos = settings.MINIO_BUCKET_PHOTOS
    out.append((backups, f"backups/{user_id}/{uuid}/source.zip"))
    if company_id:
        out.append((backups, f"backups/company_{company_id}/{uuid}/source.zip"))
    if task:
        out.append((photos, f"{photos_service.photos_prefix(task)}source.zip"))
        out.append((photos, f"photos/{task}/source.zip"))
    out.append((photos, f"{photos_service.photos_prefix(uuid)}source.zip"))
    return out


def _find_source_zip(model: Model3D, order: Order | None) -> tuple[str, str]:
    for bucket, key in _candidate_keys(model, order):
        if minio_service.object_exists(bucket, key):
            return bucket, key
    raise HTTPException(404, "Исходники в облаке не найдены или срок хранения истёк")


def _expected_sha(bucket: str, zip_key: str) -> str | None:
    # metadata рядом: …/metadata.json
    meta_key = zip_key.rsplit("/", 1)[0] + "/metadata.json"
    if not minio_service.object_exists(bucket, meta_key):
        # photos prefix metadata
        if "/source.zip" in zip_key:
            alt = zip_key.replace("source.zip", "metadata.json")
            if minio_service.object_exists(bucket, alt):
                meta_key = alt
            else:
                return None
        else:
            return None
    try:
        meta = json.loads(minio_service.download_bytes(bucket, meta_key))
    except Exception:  # noqa: BLE001
        return None
    return meta.get("archive_sha256") or meta.get("zip_sha256")


async def restore_sources(
    db: AsyncSession,
    *,
    model: Model3D,
    user: User,
    request: Request | None = None,
    expires: int = 1800,
) -> dict[str, Any]:
    """Presigned GET на source.zip + access_log + audit (§9.1.3 / §10.7.7)."""
    order = await db.get(Order, model.order_id) if model.order_id else None
    bucket, key = _find_source_zip(model, order)
    expected = _expected_sha(bucket, key)
    url = minio_service.generate_presigned_url(bucket, key, expires=expires, method="get_object")
    await access_svc.log_model_access(
        db,
        model=model,
        user=user,
        request=request,
        action="restore_sources",
        file_format="zip",
    )
    db.add(
        AuditLog(
            company_id=model.company_id,
            user_id=user.id,
            action="restore_from_cloud",
            details={
                "model_uuid": model.uuid,
                "bucket": bucket,
                "key": key,
                "source": "manual",
                "expected_sha256": expected,
            },
        )
    )
    await db.flush()
    return {
        "model_uuid": model.uuid,
        "download_url": url,
        "bucket": bucket,
        "key": key,
        "expires_in": expires,
        "zip_sha256": expected,
        "message": "Скачайте ZIP и распакуйте 12 фото локально (§9.1.3)",
    }
