"""3D-модели: скачивание, публикация WB/Ozon, share, оценка."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_db_user
from app.models import Model3D, ModelPublicationLink, User
from app.schemas.models import ModelRateRequest
from app.services import publication as pub_svc
from app.services.access import get_accessible_model, require_company_permission
from app.services.download_guard import assert_download_allowed
from app.services.minio import minio_service

router = APIRouter()


class PublishMarkRequest(BaseModel):
    marketplace: str = Field(pattern=r"^(wildberries|ozon|both)$")
    note: str | None = None


class PublicationLinkBody(BaseModel):
    url: str = Field(min_length=12, max_length=2000)


class ShareBody(BaseModel):
    ttl_days: int = Field(default=7, ge=1, le=90)


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


def _presign_glb(model: Model3D, expires: int = 3600, *, request=None) -> str | None:
    parsed = _parse_s3(model.glb_url)
    if not parsed:
        return None
    bucket, key = parsed
    if model.file_sha256:
        from app.services.integrity import verify_object_sha256

        verify_object_sha256(bucket, key, model.file_sha256)
    elif minio_service.object_exists(bucket, key):
        from app.services.integrity import sha256_bytes

        digest = sha256_bytes(minio_service.download_bytes(bucket, key))
        model.file_sha256 = digest
    return minio_service.generate_presigned_url(bucket, key, expires=expires, method="get_object")


async def _get_owned_model(db: AsyncSession, model_uuid: str, user: User) -> Model3D:
    return await get_accessible_model(db, model_uuid, user)


@router.get("/share/{short_hash}")
async def public_share(short_hash: str, db: AsyncSession = Depends(get_db)):
    """Публичный viewer без auth (§7 / §2.4)."""
    _link, model = await pub_svc.resolve_share(db, short_hash)
    url = _presign_glb(model, expires=1800)
    if not url:
        raise HTTPException(404, "GLB отсутствует")
    return {
        "short_hash": short_hash,
        "model_uuid": model.uuid,
        "preview_url": url,
        "expires_in": 1800,
        "publish_status": model.publish_status,
    }


class ImportModelBody(BaseModel):
    glb_key: str = Field(description="Ключ в MinIO models/, например imports/{uuid}/model.glb")
    category: str = "other"
    company_id: int | None = None


@router.post("/import")
async def import_model(
    body: ImportModelBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Импорт готового GLB Owner (§5 / §20) — без пайплайна TRELLIS."""
    import uuid as uuid_lib

    from app.models import Company, Order

    if body.company_id:
        company = await db.get(Company, body.company_id)
        if not company or company.owner_id != user.id:
            raise HTTPException(403, "Только Owner компании")
    if not minio_service.object_exists(settings.MINIO_BUCKET_MODELS, body.glb_key):
        raise HTTPException(400, "GLB не найден в MinIO")
    model_uuid = str(uuid_lib.uuid4())
    glb_url = f"s3://{settings.MINIO_BUCKET_MODELS}/{body.glb_key}"
    row = Model3D(
        uuid=model_uuid,
        order_id=0,
        user_id=user.id,
        company_id=body.company_id,
        glb_url=glb_url,
        publish_status="imported",
    )
    order = Order(
        user_id=user.id,
        company_id=body.company_id,
        task_uuid=str(uuid_lib.uuid4()),
        category=body.category,
        tier="small",
        status="completed",
        amount=0,
        amount_original=0,
        discount_amount=0,
        upsell_options=[],
        upsell_amount=0,
    )
    db.add(order)
    await db.flush()
    row.order_id = order.id
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"uuid": row.uuid, "glb_url": row.glb_url, "order_id": order.id, "status": "imported"}


@router.get("/{model_uuid}")
async def get_model(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    model = await _get_owned_model(db, model_uuid, user)
    links = await pub_svc.list_links(db, model.uuid)
    return {
        "uuid": model.uuid,
        "order_id": model.order_id,
        "glb_url": model.glb_url,
        "usdz_url": model.usdz_url,
        "publish_status": model.publish_status,
        "watermark_hmac": model.watermark_hmac,
        "publication_links": links,
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }


@router.get("/{model_uuid}/download")
async def download_model(
    model_uuid: str,
    request: Request,
    format: str = Query(default="glb", pattern=r"^(glb|usdz)$"),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Presigned URL для скачивания .glb / .usdz + Referer/SHA-256 (§10.3 / §9)."""
    assert_download_allowed(request)
    model = await _get_owned_model(db, model_uuid, user)
    await require_company_permission(db, user, model.company_id, "can_download_models")
    raw = model.glb_url if format == "glb" else model.usdz_url
    if format == "usdz" and not raw and model.glb_url:
        url = _presign_glb(model, expires=3600)
        if not url:
            raise HTTPException(404, "Файл модели отсутствует")
        await db.commit()
        return {
            "download_url": url,
            "format": "glb",
            "fallback": True,
            "message": "USDZ ещё не сгенерирован — отдан GLB",
            "expires_in": 3600,
            "file_sha256": model.file_sha256,
        }
    parsed = _parse_s3(raw)
    if not parsed:
        raise HTTPException(404, f"Файл {format} отсутствует")
    bucket, key = parsed
    if format == "glb":
        url = _presign_glb(model, expires=3600)
        await db.commit()
        if not url:
            raise HTTPException(404, "GLB отсутствует")
        return {
            "download_url": url,
            "format": format,
            "bucket": bucket,
            "key": key,
            "expires_in": 3600,
            "file_sha256": model.file_sha256,
        }
    url = minio_service.generate_presigned_url(bucket, key, expires=3600, method="get_object")
    return {"download_url": url, "format": format, "bucket": bucket, "key": key, "expires_in": 3600}



@router.get("/{model_uuid}/preview")
async def preview_model(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Короткий presigned URL для встроенного просмотрщика."""
    model = await _get_owned_model(db, model_uuid, user)
    url = _presign_glb(model, expires=1800)
    if not url:
        raise HTTPException(404, "GLB отсутствует")
    return {"preview_url": url, "format": "glb", "expires_in": 1800}


@router.post("/{model_uuid}/publish/mark")
async def mark_published(
    model_uuid: str,
    body: PublishMarkRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Отметка «Я опубликовал» на WB / Ozon (§7)."""
    model = await _get_owned_model(db, model_uuid, user)
    await require_company_permission(db, user, model.company_id, "can_mark_published")
    model.publish_status = f"published_{body.marketplace}"
    await db.commit()
    return {
        "uuid": model.uuid,
        "publish_status": model.publish_status,
        "marketplace": body.marketplace,
        "instructions": {
            "wildberries": "WB → Товары → Карточка → загрузить 3D (USDZ/GLB)",
            "ozon": "Ozon Seller → Контент → 3D-модель (GLB)",
        },
    }


@router.get("/{model_uuid}/publication/links")
async def get_publication_links(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_model(db, model_uuid, user)
    return {"items": await pub_svc.list_links(db, model_uuid)}


@router.post("/{model_uuid}/publication/links")
async def add_publication_link(
    model_uuid: str,
    body: PublicationLinkBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    model = await _get_owned_model(db, model_uuid, user)
    await require_company_permission(db, user, model.company_id, "can_add_publication_links")
    link = await pub_svc.add_publication_link(db, user=user, model=model, url=str(body.url))
    await db.commit()
    await db.refresh(link)
    await pub_svc.verify_link(db, link)
    await db.commit()
    return {
        "id": link.id,
        "marketplace": link.marketplace,
        "url": link.url,
        "status": link.status,
        "error_message": link.error_message,
    }


@router.post("/{model_uuid}/publication/links/{link_id}/verify")
async def verify_publication_link(
    model_uuid: str,
    link_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_model(db, model_uuid, user)
    link = await db.get(ModelPublicationLink, link_id)
    if not link or link.model_uuid != model_uuid:
        raise HTTPException(404, "Ссылка не найдена")
    await pub_svc.verify_link(db, link)
    await db.commit()
    return {
        "id": link.id,
        "status": link.status,
        "error_message": link.error_message,
        "verified_at": link.verified_at.isoformat() if link.verified_at else None,
    }


@router.post("/{model_uuid}/share")
async def create_share(
    model_uuid: str,
    body: ShareBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    model = await _get_owned_model(db, model_uuid, user)
    row = await pub_svc.create_share_link(db, user=user, model=model, ttl_days=body.ttl_days)
    await db.commit()
    base = settings.SELLER_PUBLIC_URL.rstrip("/")
    return {
        "short_hash": row.short_hash,
        "url": f"{base}/share/{row.short_hash}",
        "expires_at": row.expires_at.isoformat(),
    }


@router.post("/{model_uuid}/rate")
async def rate_model(
    model_uuid: str,
    body: ModelRateRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import ModelFeedback

    model = await _get_owned_model(db, model_uuid, user)
    existing = await db.scalar(
        select(ModelFeedback).where(
            ModelFeedback.model_uuid == model_uuid,
            ModelFeedback.user_id == user.id,
        )
    )
    if existing:
        existing.rating = body.rating
        existing.reasons = list(body.reasons or [])
    else:
        db.add(
            ModelFeedback(
                model_uuid=model_uuid,
                user_id=user.id,
                company_id=model.company_id,
                rating=body.rating,
                reasons=list(body.reasons or []),
            )
        )
    await db.commit()
    return {"ok": True, "uuid": model_uuid, "rating": body.rating, "reasons": body.reasons}