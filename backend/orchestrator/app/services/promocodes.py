"""Промокоды §8.5: bcrypt-хэш, validate/apply, usages."""

from __future__ import annotations

import base64
import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from app.core.config import settings
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models import Promocode, PromocodeUsage, User

# без похожих символов 0/O/1/l/I
_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1IL")


def generate_plain_code(length: int = 12) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def _code_cipher_key() -> bytes:
    return hashlib.sha256(settings.JWT_SECRET.encode()).digest()


def encrypt_code_for_admin(plain: str) -> str:
    data = plain.strip().upper().encode()
    key = _code_cipher_key()
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(xored).decode()


def decrypt_code_for_admin(enc: str) -> str | None:
    try:
        data = base64.urlsafe_b64decode(enc.encode())
        key = _code_cipher_key()
        plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return plain.decode()
    except Exception:  # noqa: BLE001
        return None


def code_meta(plain: str) -> dict[str, str]:
    return {"code_enc": encrypt_code_for_admin(plain)}


def reveal_code(meta: dict | None) -> str | None:
    if not isinstance(meta, dict):
        return None
    enc = meta.get("code_enc")
    if not enc:
        return None
    return decrypt_code_for_admin(str(enc))


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


PROMO_WARNING_MESSAGE = (
    "У вас осталась одна из трёх попыток ввести корректный промокод. "
    "В случае неудачи вам может быть недоступен ввод промокода на 30 дней."
)
PROMO_BLOCK_DAYS = 30
PROMO_MAX_ATTEMPTS = 3


def assert_promo_input_allowed(user: User) -> None:
    now = datetime.now(timezone.utc)
    blocked_until = user.promo_blocked_until
    if blocked_until and blocked_until > now:
        until = blocked_until.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
        raise HTTPException(
            403,
            f"Ввод промокода временно недоступен до {until}. Обратитесь в поддержку.",
        )


async def _persist_user_promo_state(
    user_id: int,
    *,
    attempts: int,
    blocked_until: datetime | None,
) -> None:
    """Отдельная транзакция — счётчик попыток не откатывается при ошибке заказа."""
    async with async_session() as sdb:
        row = await sdb.get(User, user_id)
        if not row:
            return
        row.promo_failed_attempts = attempts
        row.promo_blocked_until = blocked_until
        await sdb.commit()


async def record_promo_failure(db: AsyncSession, user: User) -> dict[str, Any]:
    """Учесть неудачную попытку; вернуть метаданные для UI."""
    assert_promo_input_allowed(user)
    attempts = int(user.promo_failed_attempts or 0) + 1
    blocked_until: datetime | None = None
    out: dict[str, Any] = {
        "failed_attempts": attempts,
        "show_warning": attempts == 2,
        "warning_message": PROMO_WARNING_MESSAGE if attempts == 2 else None,
        "blocked": False,
    }
    if attempts >= PROMO_MAX_ATTEMPTS:
        blocked_until = datetime.now(timezone.utc) + timedelta(days=PROMO_BLOCK_DAYS)
        out["blocked"] = True
        out["blocked_until"] = blocked_until.isoformat()
    await _persist_user_promo_state(user.id, attempts=attempts, blocked_until=blocked_until)
    user.promo_failed_attempts = attempts
    user.promo_blocked_until = blocked_until
    await db.flush()
    return out


async def reset_promo_attempts(db: AsyncSession, user: User) -> None:
    await _persist_user_promo_state(user.id, attempts=0, blocked_until=None)
    user.promo_failed_attempts = 0
    user.promo_blocked_until = None
    await db.flush()


async def validate_for_user(
    db: AsyncSession,
    *,
    plain: str,
    user: User,
    tier: str,
    company_id: int | None = None,
) -> dict[str, Any]:
    assert_promo_input_allowed(user)
    promo = await find_promocode(db, plain)
    if not promo:
        meta = await record_promo_failure(db, user)
        detail: dict[str, Any] = {"message": "Промокод не найден или неактивен", **meta}
        raise HTTPException(404, detail=detail)
    now = datetime.now(timezone.utc)
    if promo.expires_at and promo.expires_at < now:
        meta = await record_promo_failure(db, user)
        raise HTTPException(400, detail={"message": "Срок действия промокода истёк", **meta})
    if promo.max_uses is not None and promo.used_count >= promo.max_uses:
        meta = await record_promo_failure(db, user)
        raise HTTPException(400, detail={"message": "Лимит использований промокода исчерпан", **meta})
    if promo.tier and promo.tier != tier:
        meta = await record_promo_failure(db, user)
        raise HTTPException(400, detail={"message": f"Промокод только для тарифа {promo.tier}", **meta})
    if promo.user_id and promo.user_id != user.id:
        meta = await record_promo_failure(db, user)
        raise HTTPException(403, detail={"message": "Промокод персональный — недоступен этому пользователю", **meta})
    if promo.company_id and company_id and promo.company_id != company_id:
        meta = await record_promo_failure(db, user)
        raise HTTPException(403, detail={"message": "Промокод привязан к другой компании", **meta})
    if user.promo_failed_attempts:
        await reset_promo_attempts(db, user)
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
