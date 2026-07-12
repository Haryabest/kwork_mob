"""Админ: проверка водяного знака DWT/HMAC."""

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.core.security import require_admin
from app.core.vpn import require_vpn
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
