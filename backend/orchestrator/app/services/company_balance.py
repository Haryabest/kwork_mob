"""Корпоративный баланс §8 / §20."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Transaction, User
from app.services.access import company_for_permission
from app.services.company_members import MANAGE_ROLES, audit, get_membership, get_owned_company

DEFAULT_LOW_BALANCE = 5000
MAX_EXPORT_ROWS = 10_000


async def validate_company_tx_user_filter(
    db: AsyncSession,
    *,
    company: Company,
    actor: User,
    user_id: int | None,
) -> None:
    """Owner/Manager могут фильтровать транзакции по сотруднику §8."""
    if user_id is None:
        return
    membership = await get_membership(db, company.id, actor.id)
    role = "owner" if company.owner_id == actor.id else (membership.role if membership else None)
    if role not in MANAGE_ROLES and company.owner_id != actor.id:
        raise HTTPException(403, "Фильтр user_id доступен Owner/Manager")
    if user_id != company.owner_id:
        author = await get_membership(db, company.id, user_id)
        if not author:
            raise HTTPException(400, "user_id не является сотрудником компании")


def build_company_tx_stmt(
    company_id: int,
    *,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    tx_type: str | None = None,
):
    stmt = select(Transaction).where(Transaction.company_id == company_id)
    if user_id is not None:
        stmt = stmt.where(Transaction.user_id == user_id)
    if tx_type and tx_type != "all":
        stmt = stmt.where(Transaction.tx_type == tx_type)
    if date_from is not None:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        stmt = stmt.where(Transaction.created_at >= start)
    if date_to is not None:
        end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(Transaction.created_at <= end)
    return stmt.order_by(Transaction.id.desc())


def build_user_tx_stmt(
    user_id: int,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    tx_type: str | None = None,
):
    stmt = select(Transaction).where(Transaction.user_id == user_id)
    if tx_type and tx_type != "all":
        stmt = stmt.where(Transaction.tx_type == tx_type)
    if date_from is not None:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        stmt = stmt.where(Transaction.created_at >= start)
    if date_to is not None:
        end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(Transaction.created_at <= end)
    return stmt.order_by(Transaction.id.desc())


async def count_user_transactions(
    db: AsyncSession,
    user_id: int,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    tx_type: str | None = None,
) -> int:
    stmt = build_user_tx_stmt(
        user_id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    return int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)


async def count_company_transactions(
    db: AsyncSession,
    company_id: int,
    *,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    tx_type: str | None = None,
) -> int:
    stmt = build_company_tx_stmt(
        company_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    return int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)


def transactions_to_csv(rows: list[Transaction]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "user_id", "date", "type", "amount", "description"])
    for t in rows:
        w.writerow(
            [
                t.id,
                t.user_id or "",
                t.created_at.isoformat() if t.created_at else "",
                t.tx_type,
                t.amount,
                t.description or "",
            ]
        )
    return buf.getvalue()


async def export_company_transactions_csv(
    db: AsyncSession,
    *,
    company: Company,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    tx_type: str = "all",
) -> str:
    stmt = build_company_tx_stmt(
        company.id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    ).limit(MAX_EXPORT_ROWS)
    rows = (await db.scalars(stmt)).all()
    return transactions_to_csv(rows)


async def maybe_emit_balance_low(db: AsyncSession, company: Company) -> None:
    """Webhook balance.low + email владельцу сервиса (§8 / §12.4.1)."""
    from app.services.company_policies import policies_for_company
    from app.services import corporate_alerts as ca

    policies = policies_for_company(company)
    threshold = int(policies.get("low_balance_threshold", DEFAULT_LOW_BALANCE))
    if company.balance >= threshold:
        return
    try:
        from app.services import company_webhooks as wh

        await wh.emit(
            db,
            company_id=company.id,
            event="balance.low",
            payload={
                "company_id": company.id,
                "balance": company.balance,
                "threshold": threshold,
            },
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        await ca.alert_low_balance(db, company, threshold=threshold)
    except Exception:  # noqa: BLE001
        pass


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
    await maybe_emit_balance_low(db, company)


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
            tx_type="refund"
            if "возврат" in description.lower() or "refund" in description.lower()
            else "topup",
            description=description,
        )
    )
    await db.flush()


async def get_balance(db: AsyncSession, user: User) -> dict:
    company = await company_for_permission(db, user, "can_view_finance")
    return {"company_id": company.id, "balance": company.balance, "currency": "RUB"}


async def get_owned_company_row(db: AsyncSession, user: User) -> Company:
    return await get_owned_company(db, user)


async def topup_manual(db: AsyncSession, user: User, amount: int, note: str | None = None) -> dict:
    """Admin/owner manual credit (для тестов и ERP); прод — через ЮKassa webhook с company_id."""
    if amount <= 0:
        raise HTTPException(400, "amount > 0")
    company = await get_owned_company(db, user)
    await credit_company(
        db,
        company=company,
        amount=amount,
        user_id=user.id,
        description=note or "Пополнение баланса компании",
    )
    await audit(
        db, company_id=company.id, user_id=user.id, action="company.topup", details={"amount": amount}
    )
    return {"company_id": company.id, "balance": company.balance}
