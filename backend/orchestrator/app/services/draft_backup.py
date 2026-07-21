"""Облачный бэкап черновиков съёмки TTL 7 дней §3.3.2."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.services.minio import minio_service

TTL_DAYS = 7


def _prefix(user_id: int) -> str:
    return f"drafts/{user_id}/"


def draft_key(user_id: int, model_uuid: str) -> str:
    return f"{_prefix(user_id)}{model_uuid}/bundle.zip"


def meta_key(user_id: int, model_uuid: str) -> str:
    return f"{_prefix(user_id)}{model_uuid}/metadata.json"


def prepare_upload(user_id: int, model_uuid: str, *, metadata: dict[str, Any]) -> dict[str, Any]:
    bucket = settings.MINIO_BUCKET_BACKUPS
    try:
        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"MinIO недоступен: {exc}") from exc

    meta = {
        **metadata,
        "model_uuid": model_uuid,
        "user_id": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)).isoformat(),
    }
    meta_bytes = json.dumps(meta, ensure_ascii=False).encode("utf-8")
    minio_service.upload_bytes(bucket, meta_key(user_id, model_uuid), meta_bytes, content_type="application/json")

    zip_key = draft_key(user_id, model_uuid)
    upload_url = minio_service.generate_presigned_url(
        bucket, zip_key, expires=3600, method="put_object"
    )
    download_url = minio_service.generate_presigned_url(
        bucket, zip_key, expires=3600, method="get_object"
    )
    return {
        "model_uuid": model_uuid,
        "bucket": bucket,
        "zip_key": zip_key,
        "upload_url": upload_url,
        "download_url": download_url,
        "expires_in": 3600,
        "ttl_days": TTL_DAYS,
    }


def list_backups(user_id: int) -> list[dict[str, Any]]:
    bucket = settings.MINIO_BUCKET_BACKUPS
    prefix = _prefix(user_id)
    items: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    try:
        keys = minio_service.list_objects(bucket, prefix=prefix)
    except Exception:
        return []
    seen: set[str] = set()
    for key in keys:
        if not key.endswith("/metadata.json"):
            continue
        parts = key[len(prefix) :].split("/")
        if len(parts) < 2:
            continue
        model_uuid = parts[0]
        if model_uuid in seen:
            continue
        seen.add(model_uuid)
        try:
            raw = minio_service.download_bytes(bucket, key)
            meta = json.loads(raw.decode("utf-8"))
        except Exception:
            meta = {"model_uuid": model_uuid}
        exp = datetime.fromisoformat(meta["expires_at"].replace("Z", "+00:00")) if meta.get("expires_at") else None
        if exp and exp < now:
            continue
        zip_k = draft_key(user_id, model_uuid)
        if not minio_service.object_exists(bucket, zip_k):
            continue
        items.append(
            {
                "model_uuid": model_uuid,
                "category": meta.get("category"),
                "captured_count": meta.get("captured_count"),
                "uploaded_at": meta.get("uploaded_at"),
                "expires_at": meta.get("expires_at"),
            }
        )
    items.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
    return items


def restore_download(user_id: int, model_uuid: str) -> dict[str, Any]:
    bucket = settings.MINIO_BUCKET_BACKUPS
    zip_k = draft_key(user_id, model_uuid)
    if not minio_service.object_exists(bucket, zip_k):
        raise HTTPException(404, "Бэкап не найден или истёк")
    url = minio_service.generate_presigned_url(bucket, zip_k, expires=3600, method="get_object")
    meta_raw = None
    mk = meta_key(user_id, model_uuid)
    if minio_service.object_exists(bucket, mk):
        try:
            meta_raw = json.loads(minio_service.download_bytes(bucket, mk).decode("utf-8"))
        except Exception:
            meta_raw = None
    return {
        "model_uuid": model_uuid,
        "download_url": url,
        "metadata": meta_raw,
        "expires_in": 3600,
    }


def delete_backup(user_id: int, model_uuid: str) -> dict[str, Any]:
    bucket = settings.MINIO_BUCKET_BACKUPS
    zip_k = draft_key(user_id, model_uuid)
    mk = meta_key(user_id, model_uuid)
    if not minio_service.object_exists(bucket, zip_k) and not minio_service.object_exists(bucket, mk):
        raise HTTPException(404, "Бэкап не найден или истёк")
    prefix = f"{_prefix(user_id)}{model_uuid}/"
    deleted = minio_service.delete_prefix(bucket, prefix)
    return {"ok": True, "deleted_objects": deleted}
