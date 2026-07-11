"""Webhooks: ЮKassa."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Transaction, User
from app.services.yookassa import yookassa_service

router = APIRouter()


@router.post("/yookassa")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Обработка платежей ЮKassa (идемпотентность по payment_id)."""
    body = await request.json()
    parsed = yookassa_service.parse_webhook(body)
    payment_id = parsed.get("payment_id")
    if not payment_id:
        return {"ok": True, "ignored": True}

    if parsed.get("event") != "payment.succeeded" and parsed.get("status") != "succeeded":
        return {"ok": True, "ignored": True, "event": parsed.get("event")}

    existing = await db.scalar(select(Transaction).where(Transaction.external_id == payment_id))
    if existing:
        return {"ok": True, "idempotent": True}

    meta = parsed.get("metadata") or {}
    user_id = int(meta.get("user_id") or 0)
    amount = int(parsed.get("amount") or meta.get("amount") or 0)
    if not user_id or amount <= 0:
        return {"ok": False, "error": "bad metadata"}

    user = await db.get(User, user_id)
    if not user:
        return {"ok": False, "error": "user not found"}

    user.balance += amount
    db.add(
        Transaction(
            user_id=user.id,
            amount=amount,
            tx_type="topup",
            description="Пополнение через ЮKassa",
            external_id=payment_id,
        )
    )
    await db.commit()
    return {"ok": True, "credited": amount}
