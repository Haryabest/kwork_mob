"""Админ: проверка водяного знака DWT/HMAC."""

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_admin
from app.core.vpn import require_vpn
from app.models import Model3D
from app.services.minio import minio_service
from app.services.watermark import verify_glb_bytes


def _vpn_guard(request: Request) -> None:
    require_vpn(request)


router = APIRouter(dependencies=[Depends(_vpn_guard), Depends(require_admin)])


class VerifyMinioBody(BaseModel):
    bucket: str
    key: str


@router.post("/verify-upload")
async def verify_upload(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Пустой файл")
    return verify_glb_bytes(data)


@router.post("/verify-minio")
async def verify_minio(body: VerifyMinioBody):
    try:
        data = minio_service.download_bytes(body.bucket, body.key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(404, f"Объект не найден: {exc}") from exc
    return verify_glb_bytes(data)


@router.post("/verify-model/{model_uuid}")
async def verify_model_watermark(model_uuid: str, db: AsyncSession = Depends(get_db)):
    """Проверка HMAC водяного знака по model_uuid из MinIO §10.4."""
    model = await db.scalar(select(Model3D).where(Model3D.uuid == model_uuid))
    if not model or not model.glb_url:
        raise HTTPException(404, "Модель или GLB не найдены")
    raw = model.glb_url
    if raw.startswith("s3://"):
        bucket, key = raw[5:].split("/", 1)
    else:
        bucket = settings.MINIO_BUCKET_MODELS
        key = raw.lstrip("/")
    try:
        data = minio_service.download_bytes(bucket, key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(404, f"GLB не найден: {exc}") from exc
    out = verify_glb_bytes(data)
    out["model_uuid"] = model.uuid
    out["glb_key"] = key
    if model.watermark_hmac and out.get("extras"):
        out["stored_hmac_match"] = str(model.watermark_hmac) == str(out["extras"].get("hmac"))
    return out
