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
    removed_role = m.role
    await db.delete(m)
    await audit(
        db,
        company_id=company.id,
        user_id=actor.id,
        action="company_member_removed",
        details={"user_id": target_user_id, "role": removed_role},
    )
    if removed_role == "photographer":
        try:
            from app.services import corporate_alerts as ca

            await ca.alert_no_photographer(
                db, company_id=company.id, removed_user_id=target_user_id
            )
        except Exception:  # noqa: BLE001
            pass


async def change_role(db: AsyncSession, actor: User, target_user_id: int, role: str) -> CompanyMember:
    """Совместимость: смена по slug через company_roles."""
    from app.services.company_roles import assign_role_to_member

    return await assign_role_to_member(db, actor, target_user_id, role_slug=role)


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
    from app.services.company_policies import policies_for_company

    m = await get_membership(db, company_id, user.id)
    company = await db.get(Company, company_id)
    if company and company.owner_id == user.id:
        return
    if not m:
        raise HTTPException(403, "Нет членства в компании")

    policies = policies_for_company(company)
    # индивидуальные лимиты имеют приоритет над глобальными (§2.5.4)
    max_concurrent = m.max_concurrent_orders
    if max_concurrent is None:
        max_concurrent = int(policies.get("default_max_concurrent_orders") or 5)
    monthly_limit = m.monthly_spending_limit
    if monthly_limit is None and policies.get("default_monthly_spending_limit") is not None:
        monthly_limit = int(policies["default_monthly_spending_limit"])
    allowed = m.allowed_categories
    if not allowed:
        allowed = policies.get("default_allowed_categories") or None

    if allowed and category not in allowed:
        raise HTTPException(
            403,
            detail={
                "code": "category_forbidden",
                "message": f"Категория {category} запрещена политикой",
                "category": category,
            },
        )
    if max_concurrent:
        active = await db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.company_id == company_id,
                Order.user_id == user.id,
                Order.status.in_(("queued", "processing", "awaiting_payment", "pending")),
            )
        )
        if int(active or 0) >= max_concurrent:
            try:
                from app.services.user_events import record_event

                await record_event(
                    db,
                    event_type="photographer_limit_reached",
                    user_id=user.id,
                    company_id=company_id,
                    member_role=m.role,
                    payload={"limit": "max_concurrent_orders", "max": max_concurrent, "active": int(active or 0)},
                )
            except Exception:  # noqa: BLE001
                pass
            raise HTTPException(
                403,
                detail={
                    "code": "max_concurrent_orders",
                    "message": "Лимит одновременных заказов",
                    "max": max_concurrent,
                    "active": int(active or 0),
                },
            )
    if monthly_limit is not None:
        start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spent = await db.scalar(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.company_id == company_id,
                Order.user_id == user.id,
                Order.created_at >= start,
                Order.status.notin_(("cancelled", "failed", "pending")),
            )
        )
        if int(spent or 0) + amount > monthly_limit:
            try:
                from app.services.user_events import record_event

                await record_event(
                    db,
                    event_type="photographer_limit_reached",
                    user_id=user.id,
                    company_id=company_id,
                    member_role=m.role,
                    payload={
                        "limit": "monthly_spending",
                        "monthly_limit": monthly_limit,
                        "spent": int(spent or 0),
                        "requested": amount,
                    },
                )
            except Exception:  # noqa: BLE001
                pass
            raise HTTPException(
                403,
                detail={
                    "code": "monthly_spending_limit",
                    "message": "Месячный лимит расходов исчерпан",
                    "monthly_limit": monthly_limit,
                    "spent": int(spent or 0),
                },
            )
