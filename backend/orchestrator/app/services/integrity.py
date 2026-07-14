"""SHA-256 целостность исходников и GLB (§3.6.3 / §9 / §10)."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.services import photos as photos_service
from app.services.minio import minio_service


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_photos_zip_bytes(
    task_uuid: str,
    *,
    meta: dict[str, Any] | None = None,
    decryption_key: str | None = None,
) -> bytes:
    """ZIP: view_00…11.jpg + metadata.json."""
    from app.services import photo_encryption as photo_enc

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i, name in enumerate(photos_service.VIEW_NAMES):
            key = photos_service.view_key(task_uuid, i)
            if not minio_service.object_exists(settings.MINIO_BUCKET_PHOTOS, key):
                raise HTTPException(400, f"Нет фото {name}")
            data = minio_service.download_bytes(settings.MINIO_BUCKET_PHOTOS, key)
            data = photo_enc.maybe_decrypt(data, decryption_key)
            zf.writestr(name, data)
        payload = dict(meta or {"task_uuid": task_uuid})
        zf.writestr("metadata.json", json.dumps(payload, ensure_ascii=False, indent=2))
    return buf.getvalue()


def compute_and_store_source_zip(
    task_uuid: str,
    *,
    client_sha256: str | None = None,
    decryption_key: str | None = None,
) -> dict[str, Any]:
    """Собрать ZIP фото, посчитать SHA-256, сохранить; сверить с клиентом если передан."""
    photos_service.require_all_photos(task_uuid)
    # 1) предварительный хэш содержимого фото без metadata hash
    preliminary_meta = {"task_uuid": task_uuid}
    preliminary = build_photos_zip_bytes(
        task_uuid, meta=preliminary_meta, decryption_key=decryption_key
    )
    digest = sha256_bytes(preliminary)
    if client_sha256 and client_sha256.lower() != digest.lower():
        # клиентский ZIP мог включать zip_sha256 в metadata — допускаем совпадение после финальной сборки
        pass

    meta = {"task_uuid": task_uuid, "zip_sha256": digest}
    final = build_photos_zip_bytes(task_uuid, meta=meta, decryption_key=decryption_key)
    final_digest = sha256_bytes(final)
    # в metadata оставляем хэш содержимого фото-набора (стабильный идентификатор)
    meta["zip_sha256"] = digest
    meta["archive_sha256"] = final_digest
    final = build_photos_zip_bytes(task_uuid, meta=meta, decryption_key=decryption_key)

    if client_sha256 and client_sha256.lower() not in (digest.lower(), final_digest.lower(), sha256_bytes(final).lower()):
        # если клиент прислал хэш своего ZIP — сверяем с digest содержимого view_*.jpg без учёта metadata
        # (мобилка считает хэш своего ZIP с metadata) — пересчитаем client-compatible: только фото
        photos_only = io.BytesIO()
        with zipfile.ZipFile(photos_only, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i, name in enumerate(photos_service.VIEW_NAMES):
                key = photos_service.view_key(task_uuid, i)
                data = minio_service.download_bytes(settings.MINIO_BUCKET_PHOTOS, key)
                from app.services import photo_encryption as photo_enc

                data = photo_enc.maybe_decrypt(data, decryption_key)
                zf.writestr(name, data)
        photos_digest = sha256_bytes(photos_only.getvalue())
        if client_sha256.lower() not in (digest.lower(), final_digest.lower(), photos_digest.lower()):
            try:
                from app.services import integrity_alerts as ia
                import asyncio

                # sync context — fire-and-forget via new loop if needed
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        ia.alert_sha_mismatch(
                            task_uuid=task_uuid,
                            expected=client_sha256,
                            actual=digest,
                            context="compute_and_store_source_zip client mismatch",
                        )
                    )
                except RuntimeError:
                    asyncio.run(
                        ia.alert_sha_mismatch(
                            task_uuid=task_uuid,
                            expected=client_sha256,
                            actual=digest,
                            context="compute_and_store_source_zip client mismatch",
                        )
                    )
            except Exception:  # noqa: BLE001
                pass
            raise HTTPException(
                400,
                "SHA-256 ZIP не совпадает (повреждённый архив / неполные фото)",
            )

    prefix = photos_service.photos_prefix(task_uuid)
    zip_key = f"{prefix}source.zip"
    meta_key = f"{prefix}metadata.json"
    minio_service.upload_bytes(settings.MINIO_BUCKET_PHOTOS, zip_key, final, content_type="application/zip")
    minio_service.upload_bytes(
        settings.MINIO_BUCKET_PHOTOS,
        meta_key,
        json.dumps(meta, ensure_ascii=False).encode(),
        content_type="application/json",
    )
    return {"zip_sha256": digest, "archive_sha256": sha256_bytes(final), "zip_key": zip_key, "meta_key": meta_key}


def verify_object_sha256(bucket: str, key: str, expected: str | None) -> str:
    data = minio_service.download_bytes(bucket, key)
    digest = sha256_bytes(data)
    if expected and expected.lower() != digest.lower():
        try:
            from app.services import integrity_alerts as ia
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    ia.alert_sha_mismatch(
                        model_uuid=key,
                        expected=expected,
                        actual=digest,
                        context=f"verify_object_sha256 s3://{bucket}/{key}",
                    )
                )
            except RuntimeError:
                asyncio.run(
                    ia.alert_sha_mismatch(
                        model_uuid=key,
                        expected=expected,
                        actual=digest,
                        context=f"verify_object_sha256 s3://{bucket}/{key}",
                    )
                )
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(409, "Контрольная сумма файла не совпадает — скачивание отклонено")
    return digest


def verify_stored_zip(task_uuid: str) -> str:
    prefix = photos_service.photos_prefix(task_uuid)
    meta_key = f"{prefix}metadata.json"
    zip_key = f"{prefix}source.zip"
    if not minio_service.object_exists(settings.MINIO_BUCKET_PHOTOS, zip_key):
        return compute_and_store_source_zip(task_uuid)["zip_sha256"]
    meta: dict[str, Any] = {}
    if minio_service.object_exists(settings.MINIO_BUCKET_PHOTOS, meta_key):
        meta = json.loads(minio_service.download_bytes(settings.MINIO_BUCKET_PHOTOS, meta_key))
    expected = meta.get("archive_sha256") or meta.get("zip_sha256")
    return verify_object_sha256(settings.MINIO_BUCKET_PHOTOS, zip_key, expected)
