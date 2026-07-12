"""Возвраты: ЮKassa на карту + fallback на баланс (§8)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Transaction, User
from app.services.yookassa import yookassa_service

logger = logging.getLogger(__name__)


async def resolve_payment_id(db: AsyncSession, order: Order) -> str | None:
    if order.yookassa_payment_id:
        return order.yookassa_payment_id
    # topup с external_id по заказу
    rows = (
        await db.scalars(
            select(Transaction)
            .where(
                Transaction.user_id == order.user_id,
                Transaction.tx_type == "topup",
                Transaction.external_id.is_not(None),
            )
            .order_by(Transaction.id.desc())
            .limit(20)
        )
    ).all()
    needle = f"#{order.id}"
    for tx in rows:
        if tx.description and needle in tx.description and tx.external_id:
            return tx.external_id
    return None


async def refund_order(
    db: AsyncSession,
    order: Order,
    *,
    reason: str,
    user: User | None = None,
    prefer_card: bool = True,
) -> dict[str, Any]:
    """
    Полный возврат суммы заказа.
    1) Если есть платёж ЮKassa — create_refund на карту.
    2) Иначе (или дополнительно при charge с баланса) — кредит на баланс.
    Идемпотентность: повторный refund с тем же external_id не дублируется.
    """
    if order.amount <= 0:
        return {"refunded": False, "method": "none", "reason": "zero_amount"}

    user = user or await db.get(User, order.user_id)
    if not user:
        return {"refunded": False, "method": "none", "reason": "no_user"}

    # уже был refund по заказу?
    existing = await db.scalar(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.tx_type == "refund",
            Transaction.description.contains(f"#{order.id}"),
        )
    )
    if existing:
        return {
            "refunded": True,
            "method": "idempotent",
            "transaction_id": existing.id,
            "external_id": existing.external_id,
        }

    payment_id = await resolve_payment_id(db, order) if prefer_card else None
    card_ok = False
    yk_raw: dict | None = None
    err: str | None = None

    if payment_id and yookassa_service.configured:
        try:
            yk_raw = await yookassa_service.create_refund(
                payment_id, order.amount, reason[:250]
            )
            card_ok = True
            order.yookassa_payment_id = order.yookassa_payment_id or payment_id
            db.add(
                Transaction(
                    user_id=user.id,
                    company_id=order.company_id,
                    amount=order.amount,
                    tx_type="refund",
                    description=f"Возврат ЮKassa заказ #{order.id}: {reason}",
                    external_id=str(yk_raw.get("id") or payment_id),
                )
            )
            logger.info(
                "YooKassa refund order=%s payment=%s refund_id=%s",
                order.id,
                payment_id,
                yk_raw.get("id"),
            )
        except Exception as exc:  # noqa: BLE001
            err = str(exc)[:500]
            logger.exception("YooKassa refund failed order=%s: %s", order.id, exc)

    if not card_ok:
        # баланс (оплата была с баланса или карта недоступна)
        user.balance += order.amount
        db.add(
            Transaction(
                user_id=user.id,
                company_id=order.company_id,
                amount=order.amount,
                tx_type="refund",
                description=f"Возврат баланс заказ #{order.id}: {reason}"
                + (f" (yk_fail: {err})" if err else ""),
                external_id=None,
            )
        )
        return {
            "refunded": True,
            "method": "balance",
            "yookassa_error": err,
            "payment_id": payment_id,
        }

    return {
        "refunded": True,
        "method": "yookassa",
        "payment_id": payment_id,
        "yookassa": {"id": yk_raw.get("id") if yk_raw else None, "status": yk_raw.get("status") if yk_raw else None},
    }
