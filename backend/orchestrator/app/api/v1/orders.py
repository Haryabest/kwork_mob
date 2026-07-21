"""Заказы: создание, статус, отмена, оплата ЮKassa + очередь + фото."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_db_user
from app.models import Company, Model3D, Order, Transaction, User
from app.schemas.orders import OrderCreateRequest
from app.services import photos as photos_service
from app.services.age_gate import ensure_age_gate
from app.services.events import publish_order_status
from app.services.nsfw import nsfw_service
from app.services import promocodes as promo_svc
from app.services import tariffs as tariff_svc
from app.services import upsells as upsell_svc
from app.services.access import require_company_permission, assert_order_cancel
from app.services.company_members import enforce_member_limits
from app.services import company_balance as company_bal
from app.services.queue import queue_service
from app.services.yookassa import yookassa_service

router = APIRouter()


class PhotosPrepareRequest(BaseModel):
    task_uuid: str | None = None
    company_id: int | None = None


class PhotoEncryptionKeyBody(BaseModel):
    task_uuid: str
    key_b64: str
    algorithm: str = "aes-256-gcm"


class OrderPayRequest(BaseModel):
    payment_method: str = "redirect"
    customer_name: str | None = None


class ZipUploadInitBody(BaseModel):
    task_uuid: str
    total_size: int
    sha256: str
    chunk_size: int = 524288


class CancelOrderBody(BaseModel):
    ack_no_refund: bool = False


@router.get("/tariffs")
async def list_tariffs(
    db: AsyncSession = Depends(get_db),
):
    """Публичные тарифы для checkout §19.8."""
    return {"items": await tariff_svc.list_tariffs(db)}


async def _task_payload(
    db: AsyncSession,
    order: Order,
    user_id: int,
    photos_prefix: str | None = None,
    *,
    device_model: str | None = None,
    os_version: str | None = None,
) -> dict:
    prefix = photos_prefix or f"photos/{order.task_uuid}/"
    payload = {
        "category": order.category,
        "tier": order.tier,
        "user_id": user_id,
        "order_id": order.id,
        "company_id": order.company_id,
        "photos_bucket": settings.MINIO_BUCKET_PHOTOS,
        "photos_prefix": prefix,
        "models_bucket": settings.MINIO_BUCKET_MODELS,
        "upsell_options": order.upsell_options or [],
        "scale_calibration": order.scale_calibration,
        "device_model": device_model or order.device_model or "unknown",
        "os_version": os_version or order.os_version or "unknown",
        "target_marketplace": getattr(order, "target_marketplace", None) or "ozon",
    }
    from app.services import photo_encryption as photo_enc

    key = await photo_enc.get_key(order.task_uuid)
    if key:
        payload["photo_encryption_key"] = key
        payload["photo_encryption_alg"] = photo_enc.ALGORITHM
    return payload


@router.get("/upsells")
async def list_upsells(db: AsyncSession = Depends(get_db)):
    return {"items": await upsell_svc.list_prices(db)}


def _nsfw_http_detail(block_id: int, result: dict) -> dict:
    return {
        "code": "forbidden_content",
        "message": "Контент отклонён модерацией. Средства возвращены, аккаунт на проверке до 24ч.",
        "block_id": block_id,
        "confidence": result.get("confidence"),
        "method": result.get("method"),
    }


@router.post("/photos/prepare")
async def prepare_photos_upload(
    body: PhotosPrepareRequest,
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Presigned PUT на photos/{task_uuid}/view_00…11.jpg + access_log (§10.7.7)."""
    from app.services import access_log as access_svc

    task_uuid = body.task_uuid or str(uuid.uuid4())
    prepared = await photos_service.prepare_for_user(
        db, task_uuid, company_id=body.company_id
    )
    await access_svc.log_access(
        db,
        user_id=user.id,
        company_id=body.company_id,
        model_uuid=task_uuid,
        action="presign_put",
        request=request,
        file_format="jpg",
    )
    await db.commit()
    return prepared


@router.post("/photos/encryption-key")
async def register_photo_encryption_key(
    body: PhotoEncryptionKeyBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """§10.6.2: ключ E2E шифрования фото (отдельно от ciphertext в MinIO)."""
    from app.services import photo_encryption as photo_enc

    _ = user
    if body.algorithm != photo_enc.ALGORITHM:
        raise HTTPException(400, f"algorithm: {photo_enc.ALGORITHM}")
    try:
        await photo_enc.store_key(body.task_uuid, body.key_b64)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "ok": True,
        "task_uuid": body.task_uuid,
        "ttl_sec": photo_enc.KEY_TTL_SEC,
    }


@router.post("/photos/zip/init")
async def zip_upload_init(
    body: ZipUploadInitBody,
    user: User = Depends(get_current_db_user),
):
    """Resumable ZIP upload — init (§3.4.1)."""
    from app.services import photos_zip_upload as zip_up

    return await zip_up.init_upload(
        task_uuid=body.task_uuid,
        user_id=user.id,
        total_size=body.total_size,
        sha256=body.sha256,
        chunk_size=body.chunk_size,
    )


@router.get("/photos/zip/{upload_id}/status")
async def zip_upload_status(
    upload_id: str,
    user: User = Depends(get_current_db_user),
):
    from app.services import photos_zip_upload as zip_up

    return await zip_up.get_status(upload_id, user.id)


@router.put("/photos/zip/{upload_id}/chunk/{part_index}")
async def zip_upload_chunk(
    upload_id: str,
    part_index: int,
    request: Request,
    user: User = Depends(get_current_db_user),
):
    from app.services import photos_zip_upload as zip_up

    data = await request.body()
    return await zip_up.save_chunk(upload_id, user.id, part_index, data)


@router.post("/photos/zip/{upload_id}/complete")
async def zip_upload_complete(
    upload_id: str,
    user: User = Depends(get_current_db_user),
):
    from app.services import photos_zip_upload as zip_up

    return await zip_up.complete_upload(upload_id, user.id)


@router.post("/photos/upload")
async def upload_order_photos(
    files: list[UploadFile] = File(...),
    task_uuid: str = Query(...),
    user: User = Depends(get_current_db_user),
):
    """Multipart: ровно 12 файлов → MinIO."""
    _ = user
    return await photos_service.upload_files_to_prefix(task_uuid, files)


@router.post("/create")
async def create_order(
    body: OrderCreateRequest,
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    if body.forbidden_categories:
        raise HTTPException(
            400,
            "Вы выбрали запрещённую категорию. Заказ будет отклонён без возврата средств.",
        )
    if await nsfw_service.check_blacklist_db(db, body.category.value):
        raise HTTPException(400, "Категория в чёрном списке")

    await ensure_age_gate(
        db, user, category=body.category.value, birth_date=body.birth_date
    )

    from app.services.device_hint import device_hint_from_ua

    device_model = body.device_model
    os_version = body.os_version
    if not device_model or not os_version:
        ua_dev, ua_os = device_hint_from_ua(request.headers.get("user-agent"))
        device_model = device_model or ua_dev
        os_version = os_version or ua_os

    existing = await db.scalar(select(Order).where(Order.task_uuid == body.task_uuid))
    if existing:
        return {"id": existing.id, "status": existing.status, "idempotent": True}

    try:
        photos_service.require_all_photos(body.task_uuid)
    except HTTPException:
        raise HTTPException(
            400,
            "Загрузите 12 ракурсов в MinIO (POST /orders/photos/prepare + upload) перед созданием заказа",
        ) from None

    from app.services.company_owner_2fa import assert_owner_2fa_for_company_order
    from app.services.integrity import compute_and_store_source_zip

    await assert_owner_2fa_for_company_order(db, user, body.company_id)
    from app.services import photo_encryption as photo_enc

    enc_key = await photo_enc.get_key(body.task_uuid)
    if body.company_id and await photo_enc.encryption_enabled_for_company(db, body.company_id):
        if not enc_key:
            raise HTTPException(
                400,
                "E2E шифрование: сначала POST /orders/photos/encryption-key",
            )

    integrity = compute_and_store_source_zip(
        body.task_uuid, client_sha256=body.zip_sha256, decryption_key=enc_key
    )
    from app.services.source_insurance import store_insurance_copy

    store_insurance_copy(
        task_uuid=body.task_uuid,
        user_id=user.id,
        company_id=body.company_id,
        zip_key=integrity["zip_key"],
        meta_key=integrity.get("meta_key"),
    )

    # §10.8: NSFW до списания и до очереди
    nsfw = await nsfw_service.check_task_photos(body.task_uuid, decryption_key=enc_key)

    order_company = await db.get(Company, body.company_id) if body.company_id else None
    base_amount = await tariff_svc.get_amount_for_company(db, body.tier.value, order_company)
    upsell_codes, upsell_amount = await upsell_svc.calc_upsell_amount(
        db, [o.value for o in body.upsell_options]
    )
    if "real_scale" in upsell_codes and not body.scale_calibration:
        raise HTTPException(400, "Для real_scale укажите scale_calibration {width,height,depth} в метрах")

    order = Order(
        user_id=user.id,
        company_id=body.company_id,
        task_uuid=body.task_uuid,
        category=body.category.value,
        tier=body.tier.value,
        status="pending",
        amount=base_amount + upsell_amount,
        amount_original=base_amount,
        discount_amount=0,
        upsell_options=upsell_codes,
        upsell_amount=upsell_amount,
        scale_calibration=body.scale_calibration,
        zip_sha256=integrity["zip_sha256"],
        customer_name=body.customer_name,
        receipt_email=body.receipt_email or user.email,
        device_model=device_model,
        os_version=os_version,
        model_display_name=(body.model_display_name or "").strip() or None,
        target_marketplace=body.target_marketplace.value
        if body.target_marketplace.value != "wildberries"
        else "wb",
    )
    db.add(order)
    await db.flush()

    amount = base_amount + upsell_amount
    discount = 0
    if body.promocode:
        amount, discount, promo = await promo_svc.apply_to_amount(
            db,
            plain=body.promocode,
            user=user,
            tier=body.tier.value,
            amount=base_amount + upsell_amount,
            company_id=body.company_id,
            order_id=order.id,
        )
        order.amount = amount
        order.discount_amount = discount
        order.promocode_id = promo.id if promo else None

    photos_prefix = body.photos_prefix or photos_service.photos_prefix(body.task_uuid)
    priority = "high" if body.tier.value == "large" else "normal"

    await require_company_permission(db, user, body.company_id, "can_create_orders")
    await enforce_member_limits(
        db,
        user=user,
        company_id=body.company_id,
        category=body.category.value,
        amount=amount,
    )

    if nsfw.get("is_nsfw"):
        block = await nsfw_service.block_order(
            db, order=order, user=user, result=nsfw, refund=True, charged=False
        )
        await db.commit()
        raise HTTPException(403, detail=_nsfw_http_detail(block.id, nsfw))

    charged = False
    if body.company_id:
        company = await db.get(Company, body.company_id)
        if company and company.balance >= amount:
            await company_bal.charge_company(
                db,
                company=company,
                amount=amount,
                user=user,
                description=f"Заказ #{order.id} ({body.tier.value})",
                order_id=order.id,
            )
            charged = True
    if not charged and user.balance >= amount:
        user.balance -= amount
        db.add(
            Transaction(
                user_id=user.id,
                company_id=body.company_id,
                amount=-amount,
                tx_type="charge",
                description=f"Заказ #{order.id} ({body.tier.value})",
            )
        )
        charged = True

    if charged:
        order.status = "queued"
        await queue_service.enqueue(
            db,
            task_id=body.task_uuid,
            order_id=order.id,
            company_id=body.company_id,
            payload=await _task_payload(
                db,
                order,
                user.id,
                photos_prefix,
                device_model=device_model,
                os_version=os_version,
            ),
            priority=priority,
        )
    else:
        order.status = "awaiting_payment"

    await db.flush()
    if body.company_id:
        try:
            from app.services import corporate_alerts as ca

            await ca.check_suspicious_orders(db, company_id=body.company_id)
        except Exception:  # noqa: BLE001
            pass
    try:
        from app.services import company_webhooks as wh

        await wh.emit(
            db,
            company_id=order.company_id,
            event="order.created",
            payload={
                "order_id": order.id,
                "task_uuid": order.task_uuid,
                "status": order.status,
                "amount": order.amount,
                "tier": order.tier,
                "category": order.category,
            },
        )
    except Exception:  # noqa: BLE001
        pass
    await db.commit()
    await db.refresh(order)
    if order.status == "queued":
        await publish_order_status(
            user_id=user.id,
            order_id=order.id,
            task_id=order.task_uuid,
            status="queued",
        )
    return {
        "id": order.id,
        "status": order.status,
        "amount": order.amount,
        "upsell_amount": order.upsell_amount,
        "upsell_options": order.upsell_options,
        "balance": user.balance,
        "task_uuid": order.task_uuid,
        "photos_prefix": photos_prefix,
    }


@router.post("/{order_id}/pay")
async def pay_order(
    order_id: int,
    body: OrderPayRequest | None = None,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    body = body or OrderPayRequest()
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "Заказ не найден")
    if order.status not in ("awaiting_payment", "pending"):
        raise HTTPException(400, f"Заказ в статусе {order.status}, оплата не нужна")

    if body.customer_name and body.customer_name.strip():
        order.customer_name = body.customer_name.strip()

    from app.services import photo_encryption as photo_enc

    enc_key = await photo_enc.get_key(order.task_uuid)
    nsfw = await nsfw_service.check_task_photos(
        order.task_uuid, decryption_key=enc_key
    )
    if nsfw.get("is_nsfw"):
        block = await nsfw_service.block_order(
            db, order=order, user=user, result=nsfw, refund=True, charged=False
        )
        await db.commit()
        raise HTTPException(403, detail=_nsfw_http_detail(block.id, nsfw))

    method = body.payment_method or "redirect"
    if method == "card":
        method = "redirect"
    if method == "sbp":
        method = "sbp_qr"

    if method != "sbp_qr" and user.balance >= order.amount:
        user.balance -= order.amount
        db.add(
            Transaction(
                user_id=user.id,
                company_id=order.company_id,
                amount=-order.amount,
                tx_type="charge",
                description=f"Заказ #{order.id}",
            )
        )
        order.status = "queued"
        await queue_service.enqueue(
            db,
            task_id=order.task_uuid,
            order_id=order.id,
            company_id=order.company_id,
            payload=await _task_payload(db, order, user.id),
            priority="high" if order.tier == "large" else "normal",
        )
        await db.commit()
        await publish_order_status(
            user_id=user.id,
            order_id=order.id,
            task_id=order.task_uuid,
            status="queued",
        )
        return {"id": order.id, "status": "queued", "paid_from_balance": True}

    from app.services.tax import build_receipt_for_payment

    receipt = await build_receipt_for_payment(
        db,
        customer_email=order.receipt_email or user.email,
        description=f"Генерация 3D-модели заказ #{order.id}",
        amount_rub=order.amount,
        customer_name=order.customer_name or user.full_name,
    )
    payment = await yookassa_service.create_payment(
        order.amount,
        f"Оплата заказа #{order.id} KWork Mob",
        return_url=f"{settings.SELLER_PUBLIC_URL}/orders/{order.id}",
        metadata={
            "purpose": "order",
            "user_id": user.id,
            "order_id": order.id,
            "amount": order.amount,
            "payment_method": method,
        },
        idempotence_key=f"order-{order.id}-{order.task_uuid}-{method}",
        receipt=receipt,
        payment_method=method,  # type: ignore[arg-type]
    )
    return {
        "id": order.id,
        "status": order.status,
        "payment_id": payment["id"],
        "confirmation_url": payment.get("confirmation_url"),
        "confirmation_data": payment.get("confirmation_data"),
        "confirmation_type": payment.get("confirmation_type"),
        "payment_method": method,
        "amount": order.amount,
    }


@router.get("/{order_id}")
async def get_order(
    order_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "Заказ не найден")
    model = await db.scalar(select(Model3D).where(Model3D.order_id == order.id))
    pos = await queue_service.position_for_task(order.task_uuid)
    ewt = await queue_service.estimate_wait_time(pos) if pos else None
    return {
        "id": order.id,
        "task_uuid": order.task_uuid,
        "category": order.category,
        "tier": order.tier,
        "status": order.status,
        "amount": order.amount,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "queue_position": pos,
        "ewt_sec": ewt,
        "model": (
            {
                "uuid": model.uuid,
                "glb_url": model.glb_url,
                "publish_status": model.publish_status,
            }
            if model
            else None
        ),
    }


@router.get("/{order_id}/status")
async def order_status(
    order_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "Заказ не найден")
    pos = await queue_service.position_for_task(order.task_uuid)
    ewt = await queue_service.estimate_wait_time(pos) if pos else None
    return {
        "id": order.id,
        "status": order.status,
        "amount": order.amount,
        "task_uuid": order.task_uuid,
        "queue_position": pos,
        "ewt_sec": ewt,
    }


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    body: CancelOrderBody | None = None,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import AuditLog
    from app.services import task_lifecycle as tl

    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Заказ не найден")
    await assert_order_cancel(db, order, user)
    ack = bool(body.ack_no_refund) if body else False
    processing = order.status in ("processing", "generating")
    if processing:
        if not ack:
            raise HTTPException(
                400,
                "Отмена во время генерации требует подтверждения (без возврата средств)",
            )
        prev = order.status
        await tl.cancel_processing_order(db, order)
    elif order.status in ("pending", "queued", "paid", "awaiting_payment"):
        prev = order.status
        order.status = "cancelled"
        await queue_service.remove_from_redis(order.task_uuid)
    else:
        raise HTTPException(400, "Заказ нельзя отменить")
    db.add(
        AuditLog(
            company_id=order.company_id,
            user_id=user.id,
            action="order_cancelled",
            details={
                "order_id": order.id,
                "task_uuid": order.task_uuid,
                "previous_status": prev,
                "stage": "processing" if processing else ("queue" if prev in ("queued", "paid", "pending") else prev),
                "cancelled_by": user.id,
                "amount": order.amount,
                "no_refund": processing,
            },
        )
    )
    try:
        from app.services import company_webhooks as wh

        await wh.emit(
            db,
            company_id=order.company_id,
            event="order.cancelled",
            payload={
                "order_id": order.id,
                "task_uuid": order.task_uuid,
                "cancelled_by": user.id,
            },
        )
    except Exception:  # noqa: BLE001
        pass
    await db.commit()
    await publish_order_status(
        user_id=order.user_id,
        order_id=order.id,
        task_id=order.task_uuid,
        status="cancelled",
    )
    return {"id": order.id, "status": order.status}


@router.get("")
async def list_orders(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
    company_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None, description="Фильтр исполнитель §3.16.2"),
):
    """§3.5.3 / §3.16.2 — личные заказы или заказы компании с фильтром по сотруднику."""
    from app.services.access import assert_company_access
    from app.services.company_members import MANAGE_ROLES, get_membership

    if company_id is not None:
        company = await assert_company_access(db, user, company_id)
        membership = await get_membership(db, company_id, user.id)
        role = "owner" if company.owner_id == user.id else (membership.role if membership else None)
        if role in MANAGE_ROLES or company.owner_id == user.id:
            stmt = select(Order).where(Order.company_id == company_id)
            if user_id is not None:
                if user_id != company.owner_id:
                    author = await get_membership(db, company_id, user_id)
                    if not author:
                        raise HTTPException(400, "user_id не является сотрудником компании")
                stmt = stmt.where(Order.user_id == user_id)
        else:
            stmt = select(Order).where(Order.company_id == company_id, Order.user_id == user.id)
    else:
        if user_id is not None and user_id != user.id:
            raise HTTPException(403, "Фильтр user_id доступен только для заказов компании")
        stmt = select(Order).where(Order.user_id == user.id)
        if user_id is not None:
            stmt = stmt.where(Order.user_id == user_id)
    rows = (await db.scalars(stmt.order_by(Order.id.desc()).limit(100))).all()
    return {
        "items": [
            {
                "id": o.id,
                "task_uuid": o.task_uuid,
                "category": o.category,
                "tier": o.tier,
                "status": o.status,
                "amount": o.amount,
                "company_id": o.company_id,
                "user_id": o.user_id,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in rows
        ],
        "scope": "company" if company_id else "personal",
    }
