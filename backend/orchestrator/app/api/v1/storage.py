"""Хранилище MinIO: buckets, presigned upload/download + Referer (§10.3)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import get_current_db_user, require_admin
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


@router.post("/presign-upload")
async def presign_upload(body: PresignUploadRequest, _user=Depends(get_current_db_user)):
    """Presigned PUT на 30 мин (§9)."""
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
    return {"bucket": bucket, "key": key, "upload_url": url, "expires_in": 1800, "content_type": body.content_type}


@router.post("/presign-download")
async def presign_download(
    body: PresignDownloadRequest,
    request: Request,
    _user=Depends(get_current_db_user),
):
    """Presigned GET + CORS/Referer check (§10.3)."""
    assert_download_allowed(request)
    url = minio_service.generate_presigned_url(body.bucket, body.key, expires=body.expires, method="get_object")
    return {"download_url": url, "expires_in": body.expires}
