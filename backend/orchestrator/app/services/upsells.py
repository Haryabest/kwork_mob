"""Апсейлы §17: цены + сумма к заказу."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UpsellPrice

DEFAULTS = {
    "real_scale": ("Масштаб 1:1", 500),
    "video_360": ("Видео 360", 990),
    "virtual_tryon": ("Виртуальная примерка (USDZ)", 1500),
    "hole_filling": ("Автозаполнение пустот", 300),
}

VALID = set(DEFAULTS.keys())


async def ensure_defaults(db: AsyncSession) -> None:
    for code, (title, amount) in DEFAULTS.items():
        row = await db.get(UpsellPrice, code)
        if not row:
            db.add(UpsellPrice(code=code, title=title, amount_rub=amount, is_active=True))
    await db.flush()


async def list_prices(db: AsyncSession) -> list[dict]:
    await ensure_defaults(db)
    rows = (await db.scalars(select(UpsellPrice).order_by(UpsellPrice.code))).all()
    return [
        {"code": r.code, "title": r.title, "amount_rub": r.amount_rub, "is_active": r.is_active}
        for r in rows
        if r.is_active
    ]


async def list_all_prices(db: AsyncSession) -> list[dict]:
    """Все апсейлы для admin UI §8.4."""
    await ensure_defaults(db)
    rows = (await db.scalars(select(UpsellPrice).order_by(UpsellPrice.code))).all()
    return [
        {
            "code": r.code,
            "title": r.title,
            "amount_rub": r.amount_rub,
            "is_active": r.is_active,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


async def set_amount(
    db: AsyncSession,
    *,
    code: str,
    amount_rub: int,
    is_active: bool | None = None,
) -> UpsellPrice:
    if code not in VALID:
        raise HTTPException(404, "Апсейл не найден")
    if amount_rub < 0:
        raise HTTPException(400, "Цена не может быть отрицательной")
    await ensure_defaults(db)
    row = await db.get(UpsellPrice, code)
    if not row:
        raise HTTPException(404, "Апсейл не найден")
    row.amount_rub = amount_rub
    if is_active is not None:
        row.is_active = is_active
    await db.flush()
    return row


async def calc_upsell_amount(db: AsyncSession, options: list[str]) -> tuple[list[str], int]:
    await ensure_defaults(db)
    cleaned: list[str] = []
    total = 0
    for opt in options or []:
        if opt not in VALID:
            raise HTTPException(400, f"Неизвестная апсейл-опция: {opt}")
        if opt in cleaned:
            continue
        row = await db.get(UpsellPrice, opt)
        if not row or not row.is_active:
            raise HTTPException(400, f"Опция недоступна: {opt}")
        cleaned.append(opt)
        total += int(row.amount_rub)
    return cleaned, total
