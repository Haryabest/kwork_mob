"""Проверки доступа B2B: membership + require_permission (§2.5.3 / §10.7)."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, CompanyMember, Model3D, Order, User
from app.services.company_members import get_membership
from app.services.company_roles import require_permission, resolve_permissions


async def assert_company_access(db: AsyncSession, user: User, company_id: int) -> Company:
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    if company.owner_id == user.id:
        return company
    m = await get_membership(db, company_id, user.id)
    if not m:
        raise HTTPException(403, "Нет доступа к компании")
    return company


async def require_company_permission(
    db: AsyncSession,
    user: User,
    company_id: int | None,
    permission: str,
) -> None:
    """Личный режим (company_id is None) — без B2B-прав. Иначе membership + permission."""
    if company_id is None:
        return
    await assert_company_access(db, user, company_id)
    await require_permission(
        db, company_id=company_id, user_id=user.id, permission=permission
    )


async def company_for_permission(
    db: AsyncSession,
    user: User,
    permission: str,
    *,
    company_id: int | None = None,
) -> Company:
    """Компания, где у user есть permission (явный id, иначе owned, иначе membership)."""
    if company_id is not None:
        await require_company_permission(db, user, company_id, permission)
        company = await db.get(Company, company_id)
        assert company is not None
        return company

    owned = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
    if owned:
        await require_permission(
            db, company_id=owned.id, user_id=user.id, permission=permission
        )
        return owned

    memberships = (
        await db.scalars(select(CompanyMember).where(CompanyMember.user_id == user.id))
    ).all()
    for m in memberships:
        perms = await resolve_permissions(db, m.company_id, user.id)
        if perms.get(permission):
            company = await db.get(Company, m.company_id)
            if company:
                return company
    raise HTTPException(403, f"Нет права: {permission}")


async def get_accessible_model(db: AsyncSession, model_uuid: str, user: User) -> Model3D:
    """Владелец модели или участник компании с can_view_all_company_models."""
    model = await db.scalar(select(Model3D).where(Model3D.uuid == model_uuid))
    if not model:
        raise HTTPException(404, "Модель не найдена")
    if model.user_id == user.id:
        return model
    if model.company_id:
        perms = await resolve_permissions(db, model.company_id, user.id)
        if perms.get("can_view_all_company_models"):
            return model
    raise HTTPException(404, "Модель не найдена")


async def assert_order_cancel(db: AsyncSession, order: Order, user: User) -> None:
    if order.user_id == user.id:
        if order.company_id:
            await require_company_permission(
                db, user, order.company_id, "can_cancel_own_orders"
            )
        return
    if order.company_id:
        await require_company_permission(
            db, user, order.company_id, "can_cancel_any_orders"
        )
        return
    raise HTTPException(404, "Заказ не найден")
