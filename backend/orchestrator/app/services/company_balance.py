"""Корпоративный баланс §8 / §20."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Transaction, User
from app.services.company_members import audit, get_owned_company


async def charge_company(
    db: AsyncSession,
    *,
    company: Company,
    amount: int,
    user: User,
    description: str,
    order_id: int | None = None,
) -> None:
    if amount <= 0:
        raise HTTPException(400, "amount > 0")
    if company.balance < amount:
        raise HTTPException(402, "Недостаточно средств на балансе компании")
    company.balance -= amount
    db.add(
        Transaction(
            user_id=user.id,
            company_id=company.id,
            amount=-amount,
            tx_type="charge",
            description=description,
            external_id=f"order:{order_id}" if order_id else None,
        )
    )
    await db.flush()


async def credit_company(
    db: AsyncSession,
    *,
    company: Company,
    amount: int,
    user_id: int,
    description: str,
) -> None:
    company.balance += amount
    db.add(
        Transaction(
            user_id=user_id,
            company_id=company.id,
            amount=amount,
            tx_type="refund" if "возврат" in description.lower() or "refund" in description.lower() else "topup",
            description=description,
        )
    )
    await db.flush()


async def get_balance(db: AsyncSession, user: User) -> dict:
    company = await get_owned_company(db, user)
    return {"company_id": company.id, "balance": company.balance, "currency": "RUB"}


async def topup_manual(db: AsyncSession, user: User, amount: int, note: str | None = None) -> dict:
    """Admin/owner manual credit (для тестов и ERP); прод — через ЮKassa webhook с company_id."""
    if amount <= 0:
        raise HTTPException(400, "amount > 0")
    company = await get_owned_company(db, user)
    await credit_company(db, company=company, amount=amount, user_id=user.id, description=note or "Пополнение баланса компании")
    await audit(db, company_id=company.id, user_id=user.id, action="company.topup", details={"amount": amount})
    return {"company_id": company.id, "balance": company.balance}
