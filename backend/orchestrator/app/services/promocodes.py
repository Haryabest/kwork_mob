"""Промокоды §8.5: bcrypt-хэш, validate/apply, usages."""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import Any

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Promocode, PromocodeUsage, User

# без похожих символов 0/O/1/l/I
_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1IL")


def generate_plain_code(length: int = 12) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def hash_code(plain: str) -> str:
    normalized = plain.strip().upper()
    return bcrypt.hashpw(normalized.encode(), bcrypt.gensalt()).decode()


def verify_code(plain: str, code_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.strip().upper().encode(), code_hash.encode())
    except Exception:  # noqa: BLE001
        return False


def calc_discount(amount: int, discount_type: str, discount_value: int) -> int:
    if amount <= 0:
        return 0
    if discount_type == "percent":
        d = int(round(amount * max(0, min(100, discount_value)) / 100))
    else:
        d = max(0, discount_value)
    return min(d, amount)


async def find_promocode(db: AsyncSession, plain: str) -> Promocode | None:
    rows = (await db.scalars(select(Promocode).where(Promocode.is_active.is_(True)))).all()
    for row in rows:
        if verify_code(plain, row.code_hash):
            return row
    return None


async def validate_for_user(
    db: AsyncSession,
    *,
    plain: str,
    user: User,
    tier: str,
    company_id: int | None = None,
) -> dict[str, Any]:
    promo = await find_promocode(db, plain)
    if not promo:
        raise HTTPException(404, "Промокод не найден или неактивен")
    now = datetime.now(timezone.utc)
    if promo.expires_at and promo.expires_at < now:
        raise HTTPException(400, "Срок действия промокода истёк")
    if promo.max_uses is not None and promo.used_count >= promo.max_uses:
        raise HTTPException(400, "Лимит использований промокода исчерпан")
    if promo.tier and promo.tier != tier:
        raise HTTPException(400, f"Промокод только для тарифа {promo.tier}")
    if promo.user_id and promo.user_id != user.id:
        raise HTTPException(403, "Промокод персональный — недоступен этому пользователю")
    if promo.company_id and company_id and promo.company_id != company_id:
        raise HTTPException(403, "Промокод привязан к другой компании")
    return {
        "id": promo.id,
        "code_prefix": promo.code_prefix,
        "name": promo.name,
        "discount_type": promo.discount_type,
        "discount_value": promo.discount_value,
        "tier": promo.tier,
        "valid": True,
    }


async def apply_to_amount(
    db: AsyncSession,
    *,
    plain: str | None,
    user: User,
    tier: str,
    amount: int,
    company_id: int | None,
    order_id: int | None = None,
) -> tuple[int, int, Promocode | None]:
    """Вернуть (final_amount, discount, promo). Увеличивает used_count при order_id."""
    if not plain:
        return amount, 0, None
    await validate_for_user(db, plain=plain, user=user, tier=tier, company_id=company_id)
    promo = await find_promocode(db, plain)
    assert promo is not None
    discount = calc_discount(amount, promo.discount_type, promo.discount_value)
    final = max(0, amount - discount)
    if order_id is not None:
        promo.used_count = int(promo.used_count or 0) + 1
        db.add(
            PromocodeUsage(
                promocode_id=promo.id,
                user_id=user.id,
                company_id=company_id,
                order_id=order_id,
                discount_amount=discount,
            )
        )
    return final, discount, promo
