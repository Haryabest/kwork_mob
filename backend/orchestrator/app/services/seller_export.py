"""ZIP экспорт для ручной публикации §7.7."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Model3D, User
from app.services import publication_funnel as funnel_svc
from app.services.integrity import sha256_bytes
from app.services.marketplace_upload import _load_model_files
from app.services.minio import minio_service

INSTRUCTION_TEXT = """Публикация 3D-модели на маркетплейсах
=====================================

Wildberries:
  1. Откройте карточку товара в личном кабинете WB.
  2. Раздел «3D-модель» → загрузите model.usdz (предпочтительно) или model.glb.

Ozon:
  1. Ozon Seller → Контент → Карточка товара.
  2. Блок «3D-модель» → загрузите model.glb (до 20 МБ).

После публикации добавьте ссылку на карточку в приложении — получите бонус за верификацию.

Поддержка: support@kwork.example
"""


def build_publish_zip(model: Model3D) -> bytes:
    """Собрать ZIP: glb, usdz (если есть), инструкция, metadata.json."""
    if not model.glb_url:
        raise HTTPException(400, "GLB ещё не готов")
    glb, usdz = _load_model_files(model)
    meta = {
        "model_uuid": model.uuid,
        "order_id": model.order_id,
        "company_id": model.company_id,
        "publish_status": model.publish_status,
        "glb_bytes": len(glb),
        "has_usdz": bool(usdz),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("model.glb", glb)
        if usdz:
            zf.writestr("model.usdz", usdz)
        zf.writestr("INSTRUCTION.txt", INSTRUCTION_TEXT)
        zf.writestr("metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))
    return buf.getvalue()


async def export_publish_zip(
    db: AsyncSession,
    *,
    model: Model3D,
    user: User,
    request: Request | None = None,
    expires: int = 3600,
) -> dict[str, Any]:
    """Собрать ZIP, положить в MinIO, вернуть presigned URL."""
    if model.trashed_at:
        raise HTTPException(400, "Модель в корзине")
    zip_bytes = build_publish_zip(model)
    digest = sha256_bytes(zip_bytes)
    key = f"exports/{model.uuid}/publish.zip"
    bucket = settings.MINIO_BUCKET_MODELS
    minio_service.upload_bytes(bucket, key, zip_bytes, content_type="application/zip")
    url = minio_service.generate_presigned_url(bucket, key, expires=expires, method="get_object")
    await funnel_svc.log_download(
        db,
        model=model,
        user=user,
        request=request,
        file_format="zip",
    )
    return {
        "model_uuid": model.uuid,
        "download_url": url,
        "bucket": bucket,
        "key": key,
        "expires_in": expires,
        "zip_sha256": digest,
        "files": [f for f in ("model.glb", "model.usdz" if model.usdz_url else None, "INSTRUCTION.txt", "metadata.json") if f],
        "message": "Скачайте ZIP и загрузите файлы на маркетплейс вручную (§7.7)",
    }
