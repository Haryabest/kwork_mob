"""Тарифы в БД + история цен (§8)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tariff, TariffPriceHistory

DEFAULTS = {
    "small": ("Малый", 2990),
    "large": ("Крупный", 5990),
    "import_glb": ("Импорт GLB", 500),
}


async def ensure_defaults(db: AsyncSession) -> None:
    for code, (title, amount) in DEFAULTS.items():
        row = await db.get(Tariff, code)
        if not row:
            db.add(Tariff(code=code, title=title, amount_rub=amount, is_active=True))
    await db.flush()


async def get_amount(db: AsyncSession, tier: str) -> int:
    await ensure_defaults(db)
    row = await db.get(Tariff, tier)
    if not row or not row.is_active:
        # fallback
        return DEFAULTS.get(tier, ("", 2990))[1]
    return int(row.amount_rub)


async def list_tariffs(db: AsyncSession) -> list[dict]:
    await ensure_defaults(db)
    rows = (await db.scalars(select(Tariff).order_by(Tariff.code))).all()
    return [
        {
            "code": t.code,
            "title": t.title,
            "amount_rub": t.amount_rub,
            "is_active": t.is_active,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in rows
    ]


async def set_amount(
    db: AsyncSession,
    *,
    code: str,
    amount_rub: int,
    changed_by: int | None,
    note: str | None = None,
) -> Tariff:
    if amount_rub < 0:
        raise HTTPException(400, "Цена не может быть отрицательной")
    if amount_rub < 1 and code != "import_glb":
        raise HTTPException(400, "Цена должна быть ≥ 1")
    await ensure_defaults(db)
    row = await db.get(Tariff, code)
    if not row:
        raise HTTPException(404, "Тариф не найден")
    from app.models import AuditLog

    old = row.amount_rub
    if old == amount_rub:
        return row
    row.amount_rub = amount_rub
    row.updated_at = datetime.now(timezone.utc)
    db.add(
        TariffPriceHistory(
            tariff_code=code,
            old_amount=old,
            new_amount=amount_rub,
            changed_by_user_id=changed_by,
            note=note,
        )
    )
    # §10.7.7 / §21.4.1 — критическое событие: изменение цен
    db.add(
        AuditLog(
            company_id=None,
            user_id=changed_by,
            action="tariff_price_changed",
            details={
                "tariff_code": code,
                "old_amount": old,
                "new_amount": amount_rub,
                "note": note,
            },
        )
    )
    await db.flush()
    return row


async def price_history(db: AsyncSession, code: str | None = None, limit: int = 100) -> list[dict]:
    q = select(TariffPriceHistory).order_by(TariffPriceHistory.id.desc()).limit(limit)
    if code:
        q = q.where(TariffPriceHistory.tariff_code == code)
    rows = (await db.scalars(q)).all()
    return [
        {
            "id": h.id,
            "tariff_code": h.tariff_code,
            "old_amount": h.old_amount,
            "new_amount": h.new_amount,
            "changed_by_user_id": h.changed_by_user_id,
            "note": h.note,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in rows
    ]
