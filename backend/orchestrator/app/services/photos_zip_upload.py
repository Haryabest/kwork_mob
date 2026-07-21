"""Resumable multipart ZIP upload 12 фото (§3.4.1)."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.core.redis import get_redis
from app.services import photos as photos_service
from app.services.integrity import sha256_bytes
from app.services.minio import minio_service

REDIS_PREFIX = "zip_upload:"
DEFAULT_CHUNK_SIZE = 512 * 1024
TTL_SEC = 86400


async def _redis():
    return await get_redis()


def _meta_key(upload_id: str) -> str:
    return f"{REDIS_PREFIX}{upload_id}"


async def init_upload(
    *,
    task_uuid: str,
    user_id: int,
    total_size: int,
    sha256: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict[str, Any]:
    if total_size <= 0 or total_size > 200 * 1024 * 1024:
        raise HTTPException(400, "Некорректный размер ZIP")
    if not sha256 or len(sha256) != 64:
        raise HTTPException(400, "sha256 обязателен (64 hex)")
    upload_id = str(uuid.uuid4())
    meta = {
        "upload_id": upload_id,
        "task_uuid": task_uuid,
        "user_id": user_id,
        "total_size": total_size,
        "sha256": sha256.lower(),
        "chunk_size": chunk_size,
        "parts": [],
        "completed": False,
    }
    redis = await _redis()
    await redis.set(_meta_key(upload_id), json.dumps(meta), ex=TTL_SEC)
    return {
        "upload_id": upload_id,
        "chunk_size": chunk_size,
        "total_chunks": (total_size + chunk_size - 1) // chunk_size,
    }


async def get_status(upload_id: str, user_id: int) -> dict[str, Any]:
    meta = await _load_meta(upload_id, user_id)
    parts = sorted(int(p) for p in meta.get("parts") or [])
    chunk_size = int(meta["chunk_size"])
    total = int(meta["total_size"])
    return {
        "upload_id": upload_id,
        "task_uuid": meta["task_uuid"],
        "uploaded_parts": parts,
        "total_chunks": (total + chunk_size - 1) // chunk_size,
        "completed": bool(meta.get("completed")),
    }


async def _load_meta(upload_id: str, user_id: int) -> dict[str, Any]:
    redis = await _redis()
    raw = await redis.get(_meta_key(upload_id))
    if not raw:
        raise HTTPException(404, "Сессия загрузки не найдена")
    meta = json.loads(raw)
    if int(meta.get("user_id") or 0) != user_id:
        raise HTTPException(403, "Нет доступа к загрузке")
    return meta


async def save_chunk(upload_id: str, user_id: int, part_index: int, data: bytes) -> dict[str, Any]:
    meta = await _load_meta(upload_id, user_id)
    if meta.get("completed"):
        raise HTTPException(400, "Загрузка уже завершена")
    chunk_size = int(meta["chunk_size"])
    if part_index < 0:
        raise HTTPException(400, "part_index >= 0")
    if len(data) > chunk_size:
        raise HTTPException(400, "Чанк больше chunk_size")
    bucket = settings.MINIO_BUCKET_PHOTOS
    key = f"photos/_uploads/{upload_id}/part-{part_index:05d}"
    minio_service.upload_bytes(bucket, key, data, content_type="application/octet-stream")
    parts = set(int(p) for p in meta.get("parts") or [])
    parts.add(part_index)
    meta["parts"] = sorted(parts)
    redis = await _redis()
    await redis.set(_meta_key(upload_id), json.dumps(meta), ex=TTL_SEC)
    return {"ok": True, "part_index": part_index, "uploaded_parts": meta["parts"]}


async def complete_upload(upload_id: str, user_id: int) -> dict[str, Any]:
    meta = await _load_meta(upload_id, user_id)
    if meta.get("completed"):
        return {"ok": True, "task_uuid": meta["task_uuid"], "idempotent": True}
    task_uuid = meta["task_uuid"]
    total_size = int(meta["total_size"])
    chunk_size = int(meta["chunk_size"])
    expected_parts = (total_size + chunk_size - 1) // chunk_size
    parts = sorted(int(p) for p in meta.get("parts") or [])
    if len(parts) != expected_parts or parts != list(range(expected_parts)):
        raise HTTPException(400, f"Не все части загружены ({len(parts)}/{expected_parts})")

    bucket = settings.MINIO_BUCKET_PHOTOS
    buf = bytearray()
    for i in range(expected_parts):
        key = f"photos/_uploads/{upload_id}/part-{i:05d}"
        buf.extend(minio_service.download_bytes(bucket, key))

    if len(buf) != total_size:
        raise HTTPException(400, "Размер собранного файла не совпадает")
    digest = sha256_bytes(bytes(buf))
    if digest.lower() != str(meta["sha256"]).lower():
        raise HTTPException(400, "SHA-256 ZIP не совпадает")

    _extract_zip_to_photos(task_uuid, bytes(buf))
    minio_service.upload_bytes(
        bucket,
        f"{photos_service.photos_prefix(task_uuid)}client_source.zip",
        bytes(buf),
        content_type="application/zip",
    )
    minio_service.delete_prefix(bucket, f"photos/_uploads/{upload_id}/")

    meta["completed"] = True
    redis = await _redis()
    await redis.set(_meta_key(upload_id), json.dumps(meta), ex=TTL_SEC)
    return {"ok": True, "task_uuid": task_uuid, "sha256": digest, "photos_uploaded": photos_service.VIEW_COUNT}


def _extract_zip_to_photos(task_uuid: str, data: bytes) -> None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "Некорректный ZIP") from exc
    names = set(zf.namelist())
    bucket = settings.MINIO_BUCKET_PHOTOS
    prefix = photos_service.photos_prefix(task_uuid)
    for view_name in photos_service.VIEW_NAMES:
        if view_name not in names:
            raise HTTPException(400, f"В ZIP нет {view_name}")
        content = zf.read(view_name)
        minio_service.upload_bytes(bucket, f"{prefix}{view_name}", content, content_type="image/jpeg")
    photos_service.require_all_photos(task_uuid)
