"""3D-модели: скачивание, публикация WB/Ozon, share, оценка."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
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


class ModelRenameBody(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)


class MarketplaceUploadBody(BaseModel):
    marketplace: str = Field(pattern=r"^(wb|ozon|wildberries)$")
    sku: str = Field(min_length=1, max_length=64)


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
    company_id: int
    display_name: str | None = Field(default=None, max_length=120)
    model_uuid: str | None = Field(default=None, max_length=36)


@router.post("/import/prepare")
async def prepare_model_import(
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Presigned PUT imports/{uuid}/model.glb для Owner (§6.10)."""
    import uuid as uuid_lib

    from app.services import access_log as access_svc
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    model_uuid = str(uuid_lib.uuid4())
    key = f"imports/{model_uuid}/model.glb"
    bucket = settings.MINIO_BUCKET_MODELS
    try:
        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"MinIO недоступен: {exc}") from exc
    url = minio_service.generate_presigned_url(bucket, key, expires=1800, method="put_object")
    await access_svc.log_access(
        db,
        user_id=user.id,
        company_id=company.id,
        model_uuid=model_uuid,
        action="presign_put",
        request=request,
        file_format="glb_import",
    )
    await db.commit()
    return {
        "model_uuid": model_uuid,
        "company_id": company.id,
        "key": key,
        "upload_url": url,
        "expires_in": 1800,
        "max_bytes": 50 * 1024 * 1024,
        "content_type": "model/gltf-binary",
    }


@router.post("/import")
async def import_model(
    body: ImportModelBody,
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Импорт готового GLB Owner компании (§6.10) — без пайплайна TRELLIS."""
    import uuid as uuid_lib

    from app.models import AuditLog, Order
    from app.services import access_log as access_svc
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    if body.company_id != company.id:
        raise HTTPException(403, "company_id не совпадает с вашей компанией")
    if not body.glb_key.startswith("imports/") or not body.glb_key.endswith(".glb"):
        raise HTTPException(400, "Некорректный glb_key")
    if body.model_uuid and body.glb_key.split("/")[1] != body.model_uuid:
        raise HTTPException(400, "model_uuid не совпадает с glb_key")
    if not minio_service.object_exists(settings.MINIO_BUCKET_MODELS, body.glb_key):
        raise HTTPException(400, "GLB не найден в MinIO — сначала загрузите файл")
    model_uuid = body.model_uuid or body.glb_key.split("/")[1]
    if len(model_uuid) < 32:
        raise HTTPException(400, "Некорректный UUID модели")
    existing = await db.scalar(select(Model3D).where(Model3D.uuid == model_uuid))
    if existing:
        raise HTTPException(409, "Модель с таким UUID уже существует")
    glb_url = f"s3://{settings.MINIO_BUCKET_MODELS}/{body.glb_key}"
    row = Model3D(
        uuid=model_uuid,
        order_id=0,
        user_id=user.id,
        company_id=company.id,
        glb_url=glb_url,
        display_name=(body.display_name or "").strip() or None,
        publish_status="import_validating",
    )
    order = Order(
        user_id=user.id,
        company_id=company.id,
        task_uuid=model_uuid,
        category=body.category,
        tier="small",
        status="processing",
        amount=0,
        amount_original=0,
        discount_amount=0,
        upsell_options=[],
        upsell_amount=0,
        model_display_name=row.display_name,
    )
    db.add(order)
    await db.flush()
    row.order_id = order.id
    db.add(row)
    from app.services import import_validation as iv

    await iv.enqueue_import_validation(
        db, model=row, order=order, glb_key=body.glb_key, user=user
    )
    db.add(
        AuditLog(
            company_id=company.id,
            user_id=user.id,
            action="model_import_queued",
            details={"model_uuid": model_uuid, "category": body.category, "source": "external"},
        )
    )
    await access_svc.log_access(
        db,
        user_id=user.id,
        company_id=company.id,
        model_uuid=model_uuid,
        action="import",
        request=request,
        file_format="glb",
    )
    await db.commit()
    await db.refresh(row)
    return {
        "uuid": row.uuid,
        "glb_url": row.glb_url,
        "order_id": order.id,
        "status": "import_validating",
        "display_name": row.display_name,
        "source": "external",
    }


@router.get("/trash")
async def list_trash_models(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Корзина моделей §3.3.1 (30 дней)."""
    from app.services import model_storage as ms

    return {"items": await ms.list_trash(db, user)}


@router.get("/{model_uuid}")
async def get_model(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import model_storage as ms

    model = await _get_owned_model(db, model_uuid, user)
    links = await pub_svc.list_links(db, model.uuid)
    return {
        "uuid": model.uuid,
        "order_id": model.order_id,
        "display_name": model.display_name,
        "glb_url": model.glb_url,
        "usdz_url": model.usdz_url,
        "publish_status": model.publish_status,
        "watermark_hmac": model.watermark_hmac,
        "publication_links": links,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "storage": ms.storage_meta(model),
    }


@router.get("/{model_uuid}/download")
async def download_model(
    model_uuid: str,
    request: Request,
    format: str = Query(default="glb", pattern=r"^(glb|usdz)$"),
    marketplace: str | None = Query(default=None, pattern=r"^(wb|ozon|wildberries|both)?$"),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Presigned URL для скачивания .glb / .usdz + Referer/SHA-256 (§10.3 / §9)."""
    from app.services import publication_funnel as funnel_svc

    assert_download_allowed(request)
    model = await _get_owned_model(db, model_uuid, user)
    await require_company_permission(db, user, model.company_id, "can_download_models")
    await funnel_svc.log_download(
        db,
        model=model,
        user=user,
        request=request,
        file_format=format,
        marketplace=marketplace,
    )
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
    await db.commit()
    return {"download_url": url, "format": format, "bucket": bucket, "key": key, "expires_in": 3600}



@router.get("/{model_uuid}/preview")
async def preview_model(
    model_uuid: str,
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Короткий presigned URL для встроенного просмотрщика + access_log (§10.7.2)."""
    from app.services import access_log as access_svc

    model = await _get_owned_model(db, model_uuid, user)
    url = _presign_glb(model, expires=1800)
    if not url:
        raise HTTPException(404, "GLB отсутствует")
    await access_svc.log_model_access(
        db, model=model, user=user, request=request, action="presign_get", file_format="glb"
    )
    await db.commit()
    return {"preview_url": url, "format": "glb", "expires_in": 1800}


@router.get("/{model_uuid}/preview/stream")
async def preview_model_stream(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """GLB через API (Bearer) — обход CORS MinIO для model-viewer."""
    model = await _get_owned_model(db, model_uuid, user)
    parsed = _parse_s3(model.glb_url)
    if not parsed:
        raise HTTPException(404, "GLB отсутствует")
    bucket, key = parsed
    if not minio_service.object_exists(bucket, key):
        raise HTTPException(404, "GLB отсутствует")
    data = minio_service.download_bytes(bucket, key)
    return Response(
        content=data,
        media_type="model/gltf-binary",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.get("/{model_uuid}/thumbnail")
async def model_thumbnail(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Превью §19.4.3: thumbnail.jpg или первый ракурс view_00."""
    from app.models import Order
    from app.services.photos import view_key

    model = await _get_owned_model(db, model_uuid, user)
    # final/thumbnail.jpg в bucket models
    thumb_key = f"{model.uuid}/final/thumbnail.jpg"
    if minio_service.object_exists(settings.MINIO_BUCKET_MODELS, thumb_key):
        url = minio_service.generate_presigned_url(
            settings.MINIO_BUCKET_MODELS, thumb_key, expires=3600, method="get_object"
        )
        return {"thumbnail_url": url, "source": "final", "expires_in": 3600}

    order = await db.get(Order, model.order_id)
    if order and order.task_uuid:
        photo_key = view_key(order.task_uuid, 0)
        if minio_service.object_exists(settings.MINIO_BUCKET_PHOTOS, photo_key):
            url = minio_service.generate_presigned_url(
                settings.MINIO_BUCKET_PHOTOS, photo_key, expires=3600, method="get_object"
            )
            return {"thumbnail_url": url, "source": "photo", "expires_in": 3600}

    raise HTTPException(404, "Превью недоступно")


@router.patch("/{model_uuid}")
async def rename_model(
    model_uuid: str,
    body: ModelRenameBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Переименование модели §19.4.3."""
    model = await _get_owned_model(db, model_uuid, user)
    model.display_name = body.display_name.strip()
    await db.commit()
    return {"uuid": model.uuid, "display_name": model.display_name}


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
    from app.services.publication_funnel import emit_funnel_ch_event

    emit_funnel_ch_event(
        model_uuid=model.uuid,
        event_type="manual_marked",
        user_id=user.id,
        company_id=model.company_id,
        marketplace=body.marketplace,
    )
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


@router.post("/{model_uuid}/restore-sources")
async def restore_model_sources(
    model_uuid: str,
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Восстановить исходники из облака — presigned ZIP (§9.1.3 / §10.7.7)."""
    from app.services import restore_sources as restore_svc

    model = await _get_owned_model(db, model_uuid, user)
    if model.trashed_at:
        raise HTTPException(400, "Модель в корзине")
    await require_company_permission(db, user, model.company_id, "can_download_models")
    result = await restore_svc.restore_sources(db, model=model, user=user, request=request)
    await db.commit()
    return result


@router.post("/{model_uuid}/extend-storage")
async def extend_model_storage(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Продлить хранение исходников ещё на TTL (лимит 3×) §9.1.2."""
    from app.services import model_storage as ms

    model = await _get_owned_model(db, model_uuid, user)
    result = await ms.extend_storage(db, model=model, user=user)
    await db.commit()
    return result


@router.post("/{model_uuid}/trash")
async def trash_model(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Переместить модель в корзину на 30 дней."""
    from app.services import model_storage as ms

    model = await _get_owned_model(db, model_uuid, user)
    result = await ms.trash_model(db, model=model, user=user)
    await db.commit()
    return result


@router.post("/{model_uuid}/restore-from-trash")
async def restore_model_from_trash(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Восстановить из корзины (без оплаты)."""
    from app.services import model_storage as ms

    model = await _get_owned_model(db, model_uuid, user)
    result = await ms.restore_from_trash(db, model=model, user=user)
    await db.commit()
    return result


@router.post("/{model_uuid}/marketplace-upload")
async def marketplace_upload(
    model_uuid: str,
    body: MarketplaceUploadBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """API-публикация на WB/Ozon (§7.6 / §14.6)."""
    from app.services import marketplace_upload as mp_svc

    model = await _get_owned_model(db, model_uuid, user)
    if not model.glb_url:
        raise HTTPException(400, "GLB ещё не готов")
    result = await mp_svc.upload_model_to_marketplace(
        db,
        model=model,
        marketplace=body.marketplace,
        sku=body.sku,
        initiated_by_user_id=user.id,
    )
    await db.commit()
    return result


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