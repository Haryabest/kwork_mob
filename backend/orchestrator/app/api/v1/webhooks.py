"""Webhooks: ЮKassa (верификация через GET /payments/{id})."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import Company, Order, Transaction, User
from app.services.events import publish_order_status
from app.services.queue import queue_service
from app.services.task_lifecycle import try_queue_awaiting_orders
from app.services.yookassa import yookassa_service

router = APIRouter()


def _payment_channel_label(meta: dict, payment: dict) -> str:
    method = str(meta.get("payment_method") or "")
    pm = payment.get("payment_method") or {}
    pm_type = str(pm.get("type") or "")
    if method == "sbp_qr" or pm_type == "sbp":
        return "СБП"
    return "ЮKassa"


@router.post("/yookassa")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Обработка платежей ЮKassa (идемпотентность по payment_id)."""
    yookassa_service.require_configured()
    body = await request.json()
    parsed = yookassa_service.parse_webhook(body)
    payment_id = parsed.get("payment_id")
    if not payment_id:
        return {"ok": True, "ignored": True}

    if parsed.get("event") not in ("payment.succeeded", "payment.waiting_for_capture") and parsed.get(
        "status"
    ) != "succeeded":
        return {"ok": True, "ignored": True, "event": parsed.get("event")}

    payment = await yookassa_service.get_payment(payment_id)
    if payment.get("status") != "succeeded":
        return {"ok": True, "ignored": True, "status": payment.get("status")}

    existing = await db.scalar(select(Transaction).where(Transaction.external_id == payment_id))
    if existing:
        return {"ok": True, "idempotent": True}

    meta = payment.get("metadata") or parsed.get("metadata") or {}
    purpose = str(meta.get("purpose") or "topup")
    user_id = int(meta.get("user_id") or 0)
    amount = int(float((payment.get("amount") or {}).get("value") or parsed.get("amount") or 0))
    if not user_id or amount <= 0:
        raise HTTPException(400, "bad metadata")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(400, "user not found")

    channel = _payment_channel_label(meta, payment)

    if purpose == "company_topup":
        company_id = int(meta.get("company_id") or 0)
        company = await db.get(Company, company_id) if company_id else None
        if not company or company.owner_id != user.id:
            raise HTTPException(400, "company not found")
        company.balance += amount
        db.add(
            Transaction(
                user_id=user.id,
                company_id=company.id,
                amount=amount,
                tx_type="topup",
                description=f"Пополнение баланса компании через {channel}",
                external_id=payment_id,
            )
        )
        await db.commit()
        return {"ok": True, "company_id": company.id, "credited": amount}

    if purpose == "order":
        order_id = int(meta.get("order_id") or 0)
        order = await db.get(Order, order_id) if order_id else None
        if not order or order.user_id != user.id:
            raise HTTPException(400, "order not found")
        if order.status not in ("awaiting_payment", "pending", "paid"):
            return {"ok": True, "ignored": True, "order_status": order.status}

        from app.services.nsfw import nsfw_service

        db.add(
            Transaction(
                user_id=user.id,
                company_id=order.company_id,
                amount=amount,
                tx_type="topup",
                description=f"Оплата заказа #{order.id} через {channel}",
                external_id=payment_id,
            )
        )
        user.balance += amount

        nsfw = await nsfw_service.check_task_photos(order.task_uuid)
        if nsfw.get("is_nsfw"):
            await nsfw_service.block_order(
                db, order=order, user=user, result=nsfw, refund=True, charged=False
            )
            await db.commit()
            return {"ok": True, "order_id": order.id, "blocked_nsfw": True}

        db.add(
            Transaction(
                user_id=user.id,
                company_id=order.company_id,
                amount=-order.amount,
                tx_type="charge",
                description=f"Заказ #{order.id}",
            )
        )
        user.balance -= order.amount
        order.status = "queued"
        order.yookassa_payment_id = payment_id
        await queue_service.enqueue(
            db,
            task_id=order.task_uuid,
            order_id=order.id,
            company_id=order.company_id,
            payload={
                "category": order.category,
                "tier": order.tier,
                "user_id": user.id,
                "photos_bucket": settings.MINIO_BUCKET_PHOTOS,
                "photos_prefix": f"photos/{order.task_uuid}/",
                "models_bucket": settings.MINIO_BUCKET_MODELS,
                "zip_sha256": order.zip_sha256,
            },
            priority="high" if order.tier == "large" else "normal",
        )
        await db.commit()
        await publish_order_status(
            user_id=user.id,
            order_id=order.id,
            task_id=order.task_uuid,
            status="queued",
        )
        return {"ok": True, "order_id": order.id, "queued": True}

    # topup личного баланса
    user.balance += amount
    db.add(
        Transaction(
            user_id=user.id,
            amount=amount,
            tx_type="topup",
            description=f"Пополнение через {channel}",
            external_id=payment_id,
        )
    )
    await db.flush()
    queued = await try_queue_awaiting_orders(db, user.id)
    await db.commit()
    return {"ok": True, "credited": amount, "queued_orders": queued}
