"""Заказы: создание, статус, отмена + постановка в очередь."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user
from app.models import Order, Transaction, User
from app.schemas.orders import OrderCreateRequest
from app.services.queue import queue_service

router = APIRouter()


@router.post("/create")
async def create_order(
    body: OrderCreateRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    if body.forbidden_categories:
        raise HTTPException(
            400,
            "Вы выбрали запрещённую категорию. Заказ будет отклонён без возврата средств.",
        )
    existing = await db.scalar(select(Order).where(Order.task_uuid == body.task_uuid))
    if existing:
        return {"id": existing.id, "status": existing.status, "idempotent": True}

    amount = 2990 if body.tier.value == "small" else 5990
    order = Order(
        user_id=user.id,
        company_id=body.company_id,
        task_uuid=body.task_uuid,
        category=body.category.value,
        tier=body.tier.value,
        status="pending",
        amount=amount,
    )
    db.add(order)
    await db.flush()

    # Списание с баланса при достаточности → очередь
    if user.balance >= amount:
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
        order.status = "queued"
        await queue_service.enqueue(
            db,
            task_id=body.task_uuid,
            order_id=order.id,
            company_id=body.company_id,
            payload={
                "category": body.category.value,
                "tier": body.tier.value,
                "user_id": user.id,
            },
            priority="normal",
        )
    else:
        order.status = "awaiting_payment"

    await db.commit()
    await db.refresh(order)
    return {"id": order.id, "status": order.status, "amount": order.amount, "balance": user.balance}


@router.get("/{order_id}/status")
async def order_status(
    order_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "Заказ не найден")
    return {"id": order.id, "status": order.status, "amount": order.amount}


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "Заказ не найден")
    if order.status not in ("pending", "queued", "paid"):
        raise HTTPException(400, "Заказ нельзя отменить")
    order.status = "cancelled"
    await db.commit()
    return {"id": order.id, "status": order.status}


@router.get("")
async def list_orders(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc()).limit(100))
    ).all()
    return {
        "items": [
            {
                "id": o.id,
                "task_uuid": o.task_uuid,
                "category": o.category,
                "tier": o.tier,
                "status": o.status,
                "amount": o.amount,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in rows
        ]
    }
