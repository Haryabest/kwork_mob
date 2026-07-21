"""WB/Ozon API upload scaffold (§7.6 / §14.6)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt_field, encrypt_field
from app.models import MarketplaceCredential, MarketplaceUploadLog, Model3D
from app.services.minio import minio_service

logger = logging.getLogger(__name__)

MARKETPLACES = ("wb", "ozon")
MAX_RETRIES = 3


class MarketplaceUploadError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass
class UploadResult:
    success: bool
    external_ref: str | None = None
    http_status: int | None = None
    error: str | None = None


class MarketplaceUploader(Protocol):
    marketplace: str

    async def upload(
        self,
        *,
        sku: str,
        glb: bytes,
        usdz: bytes | None,
    ) -> UploadResult: ...


def _parse_s3(url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    if url.startswith("s3://"):
        rest = url[5:]
        bucket, _, key = rest.partition("/")
        if bucket and key:
            return bucket, key
    if "/" in url and not url.startswith("http"):
        return settings.MINIO_BUCKET_MODELS, url.lstrip("/")
    return None


def _load_model_files(model: Model3D) -> tuple[bytes, bytes | None]:
    glb_parsed = _parse_s3(model.glb_url)
    if not glb_parsed:
        raise MarketplaceUploadError("no_glb", "GLB файл отсутствует")
    bucket, key = glb_parsed
    glb = minio_service.download_bytes(bucket, key)
    usdz: bytes | None = None
    usdz_parsed = _parse_s3(model.usdz_url)
    if usdz_parsed:
        usdz = minio_service.download_bytes(usdz_parsed[0], usdz_parsed[1])
    return glb, usdz


async def get_credential(
    db: AsyncSession,
    *,
    marketplace: str,
    company_id: int | None,
) -> MarketplaceCredential | None:
    mp = marketplace.lower()
    if mp in ("wildberries", "wb"):
        mp = "wb"
    elif mp == "ozon":
        mp = "ozon"
    else:
        return None

    if company_id is not None:
        row = await db.scalar(
            select(MarketplaceCredential).where(
                MarketplaceCredential.company_id == company_id,
                MarketplaceCredential.marketplace == mp,
                MarketplaceCredential.enabled.is_(True),
            )
        )
        if row:
            return row
    return await db.scalar(
        select(MarketplaceCredential).where(
            MarketplaceCredential.company_id.is_(None),
            MarketplaceCredential.marketplace == mp,
            MarketplaceCredential.enabled.is_(True),
        )
    )


def credential_api_key(row: MarketplaceCredential) -> str:
    return decrypt_field(row.api_key_encrypted) or ""


async def upsert_credential(
    db: AsyncSession,
    *,
    marketplace: str,
    api_key: str,
    company_id: int | None = None,
    client_id: str | None = None,
    enabled: bool = True,
) -> MarketplaceCredential:
    mp = marketplace.lower()
    if mp in ("wildberries", "wb"):
        mp = "wb"
    if mp not in MARKETPLACES:
        raise HTTPException(400, "marketplace: wb | ozon")
    if not api_key.strip():
        raise HTTPException(400, "api_key обязателен")

    q = select(MarketplaceCredential).where(
        MarketplaceCredential.marketplace == mp,
        MarketplaceCredential.company_id == company_id if company_id else MarketplaceCredential.company_id.is_(None),
    )
    row = await db.scalar(q)
    if not row:
        row = MarketplaceCredential(
            company_id=company_id,
            marketplace=mp,
            api_key_encrypted=encrypt_field(api_key.strip()),
            client_id=client_id,
            enabled=enabled,
        )
        db.add(row)
    else:
        row.api_key_encrypted = encrypt_field(api_key.strip())
        row.client_id = client_id
        row.enabled = enabled
    await db.flush()
    return row


def credential_public(row: MarketplaceCredential) -> dict[str, Any]:
    key = credential_api_key(row)
    masked = f"{key[:4]}…{key[-4:]}" if len(key) >= 8 else "****"
    return {
        "id": row.id,
        "company_id": row.company_id,
        "marketplace": row.marketplace,
        "api_key_masked": masked,
        "client_id": row.client_id,
        "enabled": row.enabled,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class WildberriesUploader:
    marketplace = "wb"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base = settings.WB_API_BASE_URL.rstrip("/")
        self.path = settings.WB_3D_UPLOAD_PATH

    async def upload(self, *, sku: str, glb: bytes, usdz: bytes | None) -> UploadResult:
        url = f"{self.base}{self.path}"
        headers = {"Authorization": self.api_key}
        files: list[tuple[str, tuple[str, bytes, str]]] = [
            ("glb", (f"{sku}.glb", glb, "model/gltf-binary")),
        ]
        if usdz:
            files.append(("usdz", (f"{sku}.usdz", usdz, "model/vnd.usdz+zip")))
        data = {"sku": sku, "type": "3d_model"}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, data=data, files=files)
        if resp.status_code >= 400:
            return UploadResult(
                success=False,
                http_status=resp.status_code,
                error=resp.text[:500] or resp.reason_phrase,
            )
        ref = None
        try:
            body = resp.json()
            ref = str(body.get("id") or body.get("media_id") or body.get("task_id") or "")
        except Exception:  # noqa: BLE001
            ref = None
        return UploadResult(success=True, external_ref=ref or None, http_status=resp.status_code)


class OzonUploader:
    marketplace = "ozon"

    def __init__(self, api_key: str, client_id: str | None) -> None:
        self.api_key = api_key
        self.client_id = client_id or ""
        self.base = settings.OZON_API_BASE_URL.rstrip("/")
        self.path = settings.OZON_3D_UPLOAD_PATH

    async def upload(self, *, sku: str, glb: bytes, usdz: bytes | None) -> UploadResult:
        if not self.client_id:
            return UploadResult(success=False, error="Ozon Client-Id не настроен")
        url = f"{self.base}{self.path}"
        headers = {"Client-Id": self.client_id, "Api-Key": self.api_key}
        files = {"file": (f"{sku}.glb", glb, "model/gltf-binary")}
        payload = {"sku": sku}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, data=payload, files=files)
        if resp.status_code >= 400:
            return UploadResult(
                success=False,
                http_status=resp.status_code,
                error=resp.text[:500] or resp.reason_phrase,
            )
        ref = None
        try:
            body = resp.json()
            ref = str(body.get("result", {}).get("task_id") or body.get("task_id") or "")
        except Exception:  # noqa: BLE001
            ref = None
        return UploadResult(success=True, external_ref=ref or None, http_status=resp.status_code)


def build_uploader(cred: MarketplaceCredential) -> MarketplaceUploader:
    key = credential_api_key(cred)
    if cred.marketplace == "wb":
        return WildberriesUploader(key)
    return OzonUploader(key, cred.client_id)


async def log_attempt(
    db: AsyncSession,
    *,
    model_uuid: str,
    company_id: int | None,
    marketplace: str,
    sku: str,
    attempt: int,
    result: UploadResult,
) -> MarketplaceUploadLog:
    row = MarketplaceUploadLog(
        model_uuid=model_uuid,
        company_id=company_id,
        marketplace=marketplace,
        sku=sku,
        attempt=attempt,
        status="success" if result.success else "failed",
        http_status=result.http_status,
        error_message=result.error,
        external_ref=result.external_ref,
    )
    db.add(row)
    await db.flush()
    return row


async def upload_model_to_marketplace(
    db: AsyncSession,
    *,
    model: Model3D,
    marketplace: str,
    sku: str,
    initiated_by_user_id: int | None = None,
) -> dict[str, Any]:
    """Загрузка модели через API маркетплейса с retry×3 (§14.6.4)."""
    if not settings.MARKETPLACE_UPLOAD_ENABLED:
        raise HTTPException(409, "API-публикация отключена (MARKETPLACE_UPLOAD_ENABLED=0)")

    mp = marketplace.lower()
    if mp in ("wildberries", "wb"):
        mp = "wb"
    elif mp == "ozon":
        mp = "ozon"
    else:
        raise HTTPException(400, "marketplace: wb | ozon")

    sku_clean = sku.strip()
    if not sku_clean:
        raise HTTPException(400, "sku обязателен")

    cred = await get_credential(db, marketplace=mp, company_id=model.company_id)
    if not cred:
        raise HTTPException(404, f"API-ключ {mp} не настроен")

    glb, usdz = _load_model_files(model)
    if mp == "ozon" and len(glb) > 20 * 1024 * 1024:
        raise HTTPException(400, "GLB для Ozon > 20 МБ")
    if mp == "wb" and len(glb) > 25 * 1024 * 1024:
        raise HTTPException(400, "GLB для WB > 25 МБ")

    uploader = build_uploader(cred)
    max_retries = max(1, min(settings.MARKETPLACE_UPLOAD_MAX_RETRIES, MAX_RETRIES))
    last_result: UploadResult | None = None
    logs: list[dict] = []

    for attempt in range(1, max_retries + 1):
        try:
            last_result = await uploader.upload(sku=sku_clean, glb=glb, usdz=usdz)
        except httpx.HTTPError as exc:
            last_result = UploadResult(success=False, error=str(exc)[:500])
        log_row = await log_attempt(
            db,
            model_uuid=model.uuid,
            company_id=model.company_id,
            marketplace=mp,
            sku=sku_clean,
            attempt=attempt,
            result=last_result,
        )
        logs.append(
            {
                "attempt": attempt,
                "status": log_row.status,
                "http_status": log_row.http_status,
                "error": log_row.error_message,
            }
        )
        logger.info(
            "marketplace upload model=%s mp=%s attempt=%s status=%s user=%s",
            model.uuid,
            mp,
            attempt,
            log_row.status,
            initiated_by_user_id,
        )
        if last_result.success:
            model.publish_status = f"verified_{mp}"
            await db.flush()
            try:
                from app.services.user_events import record_event

                await record_event(
                    db,
                    event_type="publication_verified",
                    user_id=initiated_by_user_id or model.user_id,
                    company_id=model.company_id,
                    payload={
                        "model_uuid": model.uuid,
                        "marketplace": mp,
                        "method": "api_upload",
                        "external_ref": last_result.external_ref,
                    },
                )
            except Exception:  # noqa: BLE001
                pass
            return {
                "ok": True,
                "model_uuid": model.uuid,
                "marketplace": mp,
                "sku": sku_clean,
                "external_ref": last_result.external_ref,
                "publish_status": model.publish_status,
                "attempts": logs,
            }

    raise HTTPException(
        502,
        detail={
            "code": "marketplace_upload_failed",
            "message": last_result.error if last_result else "upload failed",
            "attempts": logs,
        },
    )


async def model_upload_status(
    db: AsyncSession,
    *,
    model: Model3D,
) -> dict[str, Any]:
    """Статус API-публикации для селлера: credentials + последние попытки."""
    creds: dict[str, bool] = {}
    for mp in MARKETPLACES:
        creds[mp] = (await get_credential(db, marketplace=mp, company_id=model.company_id)) is not None
    logs = await list_upload_logs(db, model_uuid=model.uuid, limit=20)
    last_by_mp: dict[str, dict | None] = {"wb": None, "ozon": None}
    for row in logs:
        mp = row.get("marketplace")
        if mp in last_by_mp and last_by_mp[mp] is None:
            last_by_mp[mp] = row
    return {
        "upload_enabled": settings.MARKETPLACE_UPLOAD_ENABLED,
        "credentials": creds,
        "publish_status": model.publish_status,
        "last_attempt": last_by_mp,
        "recent_logs": logs[:10],
    }


async def list_upload_logs(
    db: AsyncSession,
    *,
    model_uuid: str | None = None,
    company_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    q = select(MarketplaceUploadLog).order_by(MarketplaceUploadLog.id.desc()).limit(limit)
    if model_uuid:
        q = q.where(MarketplaceUploadLog.model_uuid == model_uuid)
    if company_id is not None:
        q = q.where(MarketplaceUploadLog.company_id == company_id)
    rows = (await db.scalars(q)).all()
    return [
        {
            "id": r.id,
            "model_uuid": r.model_uuid,
            "company_id": r.company_id,
            "marketplace": r.marketplace,
            "sku": r.sku,
            "attempt": r.attempt,
            "status": r.status,
            "http_status": r.http_status,
            "error_message": r.error_message,
            "external_ref": r.external_ref,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
