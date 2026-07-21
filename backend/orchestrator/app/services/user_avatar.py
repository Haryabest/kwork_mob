"""Аватар пользователя §20.8.1."""

from __future__ import annotations

import uuid as uuid_lib

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User
from app.services.minio import minio_service

ALLOWED_EXT = frozenset({".jpg", ".jpeg", ".png", ".webp"})
MIME_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_BYTES = 2 * 1024 * 1024


def presigned_avatar_url(avatar_key: str | None, *, expires: int = 3600) -> str | None:
    if not avatar_key:
        return None
    bucket = settings.MINIO_BUCKET_MODELS
    if not minio_service.object_exists(bucket, avatar_key):
        return None
    return minio_service.generate_presigned_url(bucket, avatar_key, expires=expires, method="get_object")


async def upload_avatar(db: AsyncSession, *, user: User, file: UploadFile) -> dict:
    name = (file.filename or "avatar").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_EXT:
        ct = (file.content_type or "").lower()
        ext = MIME_EXT.get(ct, "")
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Форматы: JPG, PNG, WebP")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Пустой файл")
    if len(data) > MAX_BYTES:
        raise HTTPException(400, "Файл больше 2 МБ")

    key = f"avatars/{user.id}/{uuid_lib.uuid4().hex}{ext}"
    bucket = settings.MINIO_BUCKET_MODELS
    content_type = file.content_type or "image/jpeg"
    minio_service.ensure_buckets()
    minio_service.upload_bytes(bucket, key, data, content_type=content_type)
    user.avatar_key = key
    await db.flush()
    return {
        "avatar_key": key,
        "avatar_url": presigned_avatar_url(key),
        "size": len(data),
    }


async def delete_avatar(db: AsyncSession, *, user: User) -> dict:
    user.avatar_key = None
    await db.flush()
    return {"ok": True, "avatar_url": None}
