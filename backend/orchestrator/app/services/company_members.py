"""B2B: участники, роли, лимиты, сессии (§2.5)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Company, CompanyMember, Order, RefreshToken, User

ROLES = ("owner", "manager", "photographer", "viewer")
MANAGE_ROLES = ("owner", "manager")


async def get_owned_company(db: AsyncSession, user: User) -> Company:
    company = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
    if not company:
        raise HTTPException(403, "Только Owner компании")
    return company


async def get_membership(db: AsyncSession, company_id: int, user_id: int) -> CompanyMember | None:
    return await db.scalar(
        select(CompanyMember).where(
            CompanyMember.company_id == company_id,
            CompanyMember.user_id == user_id,
        )
    )


async def require_manager(db: AsyncSession, user: User) -> tuple[Company, str]:
    company = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
    if company:
        return company, "owner"
    m = await db.scalar(
        select(CompanyMember).where(
            CompanyMember.user_id == user.id,
            CompanyMember.role.in_(MANAGE_ROLES),
        ).limit(1)
    )
    if not m:
        raise HTTPException(403, "Нужна роль Owner/Manager")
    company = await db.get(Company, m.company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    return company, m.role


async def audit(db: AsyncSession, *, company_id: int, user_id: int, action: str, details: dict | None = None) -> None:
    db.add(AuditLog(company_id=company_id, user_id=user_id, action=action, details=details or {}))


async def remove_member(db: AsyncSession, actor: User, target_user_id: int) -> None:
    company = await get_owned_company(db, actor)
    if target_user_id == company.owner_id:
        raise HTTPException(400, "Нельзя удалить Owner")
    m = await get_membership(db, company.id, target_user_id)
    if not m:
        raise HTTPException(404, "Участник не найден")
    await db.delete(m)
    await audit(db, company_id=company.id, user_id=actor.id, action="member.remove", details={"user_id": target_user_id})


async def change_role(db: AsyncSession, actor: User, target_user_id: int, role: str) -> CompanyMember:
    if role not in ROLES or role == "owner":
        raise HTTPException(400, f"role: {', '.join(r for r in ROLES if r != 'owner')}")
    company = await get_owned_company(db, actor)
    if target_user_id == company.owner_id:
        raise HTTPException(400, "Роль Owner не меняется")
    m = await get_membership(db, company.id, target_user_id)
    if not m:
        raise HTTPException(404, "Участник не найден")
    old = m.role
    m.role = role
    await audit(
        db,
        company_id=company.id,
        user_id=actor.id,
        action="member.role",
        details={"user_id": target_user_id, "from": old, "to": role},
    )
    await db.flush()
    return m


async def change_limits(
    db: AsyncSession,
    actor: User,
    target_user_id: int,
    *,
    max_concurrent_orders: int | None,
    monthly_spending_limit: int | None,
    allowed_categories: list[str] | None,
) -> CompanyMember:
    company, _ = await require_manager(db, actor)
    m = await get_membership(db, company.id, target_user_id)
    if not m and target_user_id != company.owner_id:
        raise HTTPException(404, "Участник не найден")
    if not m:
        raise HTTPException(400, "Лимиты Owner задаются в settings компании")
    if max_concurrent_orders is not None:
        m.max_concurrent_orders = max_concurrent_orders
    if monthly_spending_limit is not None:
        m.monthly_spending_limit = monthly_spending_limit
    if allowed_categories is not None:
        m.allowed_categories = allowed_categories
    await audit(
        db,
        company_id=company.id,
        user_id=actor.id,
        action="member.limits",
        details={
            "user_id": target_user_id,
            "max_concurrent_orders": m.max_concurrent_orders,
            "monthly_spending_limit": m.monthly_spending_limit,
            "allowed_categories": m.allowed_categories,
        },
    )
    await db.flush()
    return m


async def member_tasks(db: AsyncSession, actor: User, target_user_id: int) -> list[dict]:
    company, _ = await require_manager(db, actor)
    m = await get_membership(db, company.id, target_user_id)
    if not m and target_user_id != company.owner_id:
        raise HTTPException(404, "Участник не найден")
    rows = (
        await db.scalars(
            select(Order)
            .where(Order.company_id == company.id, Order.user_id == target_user_id)
            .order_by(Order.id.desc())
            .limit(100)
        )
    ).all()
    return [
        {
            "id": o.id,
            "task_uuid": o.task_uuid,
            "status": o.status,
            "amount": o.amount,
            "category": o.category,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in rows
    ]


async def list_sessions(db: AsyncSession, actor: User, member_user_id: int) -> list[dict]:
    company, _ = await require_manager(db, actor)
    m = await get_membership(db, company.id, member_user_id)
    if not m and member_user_id != company.owner_id:
        raise HTTPException(404, "Участник не найден")
    tokens = (
        await db.scalars(
            select(RefreshToken)
            .where(RefreshToken.user_id == member_user_id)
            .order_by(RefreshToken.id.desc())
            .limit(50)
        )
    ).all()
    return [
        {
            "id": t.id,
            "jti": t.jti,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "revoked": t.revoked,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tokens
    ]


async def revoke_sessions(db: AsyncSession, actor: User, member_user_id: int) -> int:
    company, _ = await require_manager(db, actor)
    m = await get_membership(db, company.id, member_user_id)
    if not m and member_user_id != company.owner_id:
        raise HTTPException(404, "Участник не найден")
    tokens = (
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == member_user_id,
                RefreshToken.revoked.is_(False),
            )
        )
    ).all()
    for t in tokens:
        t.revoked = True
    await audit(
        db,
        company_id=company.id,
        user_id=actor.id,
        action="member.sessions_revoke",
        details={"user_id": member_user_id, "count": len(tokens)},
    )
    await db.flush()
    return len(tokens)


async def enforce_member_limits(
    db: AsyncSession,
    *,
    user: User,
    company_id: int | None,
    category: str,
    amount: int,
) -> None:
    if not company_id:
        return
    m = await get_membership(db, company_id, user.id)
    company = await db.get(Company, company_id)
    if company and company.owner_id == user.id:
        return
    if not m:
        raise HTTPException(403, "Нет членства в компании")
    if m.allowed_categories and category not in m.allowed_categories:
        raise HTTPException(403, f"Категория {category} запрещена политикой")
    if m.max_concurrent_orders:
        active = await db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.company_id == company_id,
                Order.user_id == user.id,
                Order.status.in_(("queued", "processing", "awaiting_payment", "pending")),
            )
        )
        if int(active or 0) >= m.max_concurrent_orders:
            raise HTTPException(403, "Лимит одновременных заказов")
    if m.monthly_spending_limit is not None:
        start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spent = await db.scalar(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.company_id == company_id,
                Order.user_id == user.id,
                Order.created_at >= start,
                Order.status.notin_(("cancelled", "failed", "pending")),
            )
        )
        if int(spent or 0) + amount > m.monthly_spending_limit:
            raise HTTPException(403, "Месячный лимит расходов исчерпан")
