"""Импорт GLB Owner/API §6.10 — одиночный и bulk до 100."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog, Model3D, Order, User
from app.services.company_balance import charge_company
from app.services import import_validation as iv
from app.services.minio import minio_service
from app.services import tariffs as tariff_svc

MAX_BULK_IMPORT = 100


async def get_import_price(db: AsyncSession) -> int:
    return await tariff_svc.get_amount(db, "import_glb")


async def queue_single_import(
    db: AsyncSession,
    *,
    company,
    user: User,
    glb_key: str,
    category: str,
    display_name: str | None,
    model_uuid: str | None = None,
    charge: bool = True,
) -> dict:
    price = await get_import_price(db)
    if charge and price > 0 and company.balance < price:
        raise HTTPException(402, "Недостаточно средств на балансе компании")
    if not glb_key.startswith("imports/") or not glb_key.endswith(".glb"):
        raise HTTPException(400, "Некорректный glb_key")
    if model_uuid and glb_key.split("/")[1] != model_uuid:
        raise HTTPException(400, "model_uuid не совпадает с glb_key")
    model_uuid = model_uuid or glb_key.split("/")[1]
    if len(model_uuid) < 32:
        raise HTTPException(400, "Некорректный UUID модели")
    if not minio_service.object_exists(settings.MINIO_BUCKET_MODELS, glb_key):
        raise HTTPException(400, "GLB не найден в MinIO — сначала загрузите файл")
    existing = await db.scalar(select(Model3D).where(Model3D.uuid == model_uuid))
    if existing:
        raise HTTPException(409, "Модель с таким UUID уже существует")

    glb_url = f"s3://{settings.MINIO_BUCKET_MODELS}/{glb_key}"
    row = Model3D(
        uuid=model_uuid,
        order_id=0,
        user_id=user.id,
        company_id=company.id,
        glb_url=glb_url,
        display_name=(display_name or "").strip() or None,
        publish_status="import_validating",
    )
    order = Order(
        user_id=user.id,
        company_id=company.id,
        task_uuid=model_uuid,
        category=category,
        tier="small",
        status="processing",
        amount=price,
        amount_original=price,
        discount_amount=0,
        upsell_options=[],
        upsell_amount=0,
        model_display_name=row.display_name,
    )
    db.add(order)
    await db.flush()
    row.order_id = order.id
    db.add(row)
    if charge and price > 0:
        await charge_company(
            db,
            company=company,
            amount=price,
            user=user,
            description=f"Импорт GLB {model_uuid}",
            order_id=order.id,
        )
    await iv.enqueue_import_validation(db, model=row, order=order, glb_key=glb_key, user=user)
    db.add(
        AuditLog(
            company_id=company.id,
            user_id=user.id,
            action="model_import_queued",
            details={"model_uuid": model_uuid, "category": category, "source": "external"},
        )
    )
    await db.flush()
    return {
        "uuid": row.uuid,
        "glb_url": row.glb_url,
        "order_id": order.id,
        "status": "import_validating",
        "display_name": row.display_name,
        "source": "external",
        "import_price_rub": price,
    }
