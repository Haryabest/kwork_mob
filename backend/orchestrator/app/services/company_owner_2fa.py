"""2FA TOTP для Owner компании (§10 / §2.4)."""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user
from app.models import Company, CompanyMember, User


async def user_is_company_owner(db: AsyncSession, user: User) -> bool:
    owned = await db.scalar(select(Company.id).where(Company.owner_id == user.id).limit(1))
    if owned:
        return True
    m = await db.scalar(
        select(CompanyMember.id).where(
            CompanyMember.user_id == user.id,
            CompanyMember.role == "owner",
        ).limit(1)
    )
    return m is not None


async def require_owner_2fa_if_needed(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Owner без TOTP не может управлять компанией / корпоративными заказами (§10)."""
    if await user_is_company_owner(db, user) and not user.totp_enabled:
        raise HTTPException(
            403,
            detail={
                "code": "owner_2fa_required",
                "message": "Owner компании обязан включить 2FA (TOTP) перед операциями с компанией",
            },
        )
    return user


async def assert_owner_2fa_for_company_order(db: AsyncSession, user: User, company_id: int | None) -> None:
    if not company_id:
        return
    from app.services.company_policies import policies_for_company

    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    policies = policies_for_company(company)
    # Owner компании (создатель) обязан иметь 2FA
    owner = await db.get(User, company.owner_id)
    if owner and not owner.totp_enabled:
        raise HTTPException(
            403,
            detail={
                "code": "owner_2fa_required",
                "message": "Owner компании обязан настроить 2FA. Операции компании заблокированы.",
            },
        )
    if user.id == company.owner_id and not user.totp_enabled:
        raise HTTPException(
            403,
            detail={
                "code": "owner_2fa_required",
                "message": "Включите 2FA (TOTP) в настройках аккаунта",
            },
        )
    # §2.5.4 require_2fa_for_all — любой сотрудник
    if policies.get("require_2fa_for_all") and not user.totp_enabled:
        raise HTTPException(
            403,
            detail={
                "code": "company_2fa_required",
                "message": "Политика компании требует 2FA для всех сотрудников",
            },
        )
