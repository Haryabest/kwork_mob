"""Хранилище MinIO: buckets, presigned upload/download + Referer (§10.3)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_db_user, require_admin
from app.models import User
from app.services.download_guard import assert_download_allowed
from app.services.minio import minio_service

router = APIRouter(prefix="/storage", tags=["Хранилище MinIO"])


class PresignUploadRequest(BaseModel):
    purpose: str = Field(pattern=r"^(photos|models|backups|logs)$")
    filename: str = ""
    content_type: str = "application/octet-stream"


class PresignDownloadRequest(BaseModel):
    bucket: str
    key: str
    expires: int = Field(default=3600, ge=60, le=3600)


@router.get("/health")
async def storage_health(_: dict = Depends(require_admin)):
    return minio_service.health()


@router.get("/smart")
async def storage_smart(_: dict = Depends(require_admin)):
    """MinIO usage + диск-алерт (§21 SMART dashboard)."""
    return minio_service.smart()


@router.post("/init")
async def init_buckets(_: dict = Depends(require_admin)):
    created = minio_service.ensure_buckets()
    return {"created": created, "buckets": minio_service.buckets}


@router.get("/encryption")
async def storage_encryption(_: dict = Depends(require_admin)):
    """Статус SSE-S3 / SSE-KMS §10.6.3."""
    return minio_service.encryption_status()


@router.post("/encryption/apply")
async def apply_bucket_encryption(_: dict = Depends(require_admin)):
    """Применить default encryption ко всем бакетам по MINIO_SSE_MODE."""
    minio_service.ensure_buckets()
    return {"ok": True, "encryption": minio_service.encryption_status()}


@router.post("/presign-upload")
async def presign_upload(
    body: PresignUploadRequest,
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Presigned PUT на 30 мин (§9) + access_log (§10.7.7)."""
    from app.services import access_log as access_svc

    bucket_map = {
        "photos": settings.MINIO_BUCKET_PHOTOS,
        "models": settings.MINIO_BUCKET_MODELS,
        "backups": settings.MINIO_BUCKET_BACKUPS,
        "logs": "logs",
    }
    bucket = bucket_map[body.purpose]
    try:
        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"MinIO недоступен: {exc}") from exc
    key = minio_service.uuid_key(body.purpose, body.filename)
    url = minio_service.generate_presigned_url(bucket, key, expires=1800, method="put_object")
    uuid_part = key.split("/")[-2] if "/" in key else key[:36]
    await access_svc.log_access(
        db,
        user_id=user.id,
        model_uuid=str(uuid_part)[:36],
        action="presign_put",
        request=request,
        file_format=body.purpose[:10],
    )
    await db.commit()
    return {
        "bucket": bucket,
        "key": key,
        "upload_url": url,
        "expires_in": 1800,
        "content_type": body.content_type,
        "sse": minio_service.sse_mode(),
    }


@router.post("/presign-download")
async def presign_download(
    body: PresignDownloadRequest,
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Presigned GET + CORS/Referer check (§10.3) + access_log (§10.7.2)."""
    from app.services import access_log as access_svc

    assert_download_allowed(request)
    url = minio_service.generate_presigned_url(
        body.bucket, body.key, expires=body.expires, method="get_object"
    )
    uuid_part = body.key.split("/")[-2] if "/" in body.key else body.key[:36]
    await access_svc.log_access(
        db,
        user_id=user.id,
        model_uuid=str(uuid_part)[:36],
        action="presign_get",
        request=request,
        file_format=body.bucket[:10],
    )
    await db.commit()
    return {"download_url": url, "expires_in": body.expires}
