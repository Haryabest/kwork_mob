"""Кастомные роли компании §2.5.3 / §20.5.5."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CompanyMember, CompanyRole
from app.services.company_members import audit, get_membership
from app.services.permissions import (
    PERMISSION_KEYS,
    SYSTEM_ROLE_PERMS,
    merge_system,
    normalize_permissions,
)


async def _company_for_roles(db: AsyncSession, user):
    from app.services.access import company_for_permission

    return await company_for_permission(db, user, "can_manage_roles")


async def ensure_system_roles(db: AsyncSession, company_id: int) -> list[CompanyRole]:
    """Создаёт предопределённые роли Owner/Manager/Photographer/Viewer для компании."""
    existing = (
        await db.scalars(select(CompanyRole).where(CompanyRole.company_id == company_id))
    ).all()
    by_slug = {r.slug: r for r in existing}
    out: list[CompanyRole] = []
    titles = {
        "owner": "Owner",
        "manager": "Manager",
        "photographer": "Photographer",
        "viewer": "Viewer",
    }
    for slug, title in titles.items():
        if slug in by_slug:
            out.append(by_slug[slug])
            continue
        row = CompanyRole(
            company_id=company_id,
            name=title,
            slug=slug,
            permissions=merge_system(slug),
            is_system=True,
        )
        db.add(row)
        await db.flush()
        out.append(row)
    return out


async def list_roles(db: AsyncSession, user) -> list[dict]:
    company = await _company_for_roles(db, user)
    roles = await ensure_system_roles(db, company.id)
    await db.flush()
    roles = (
        await db.scalars(
            select(CompanyRole).where(CompanyRole.company_id == company.id).order_by(CompanyRole.id)
        )
    ).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "slug": r.slug,
            "permissions": r.permissions,
            "is_system": r.is_system,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in roles
    ]


async def create_custom_role(
    db: AsyncSession,
    user,
    *,
    name: str,
    permissions: dict,
) -> CompanyRole:
    company = await _company_for_roles(db, user)
    await ensure_system_roles(db, company.id)
    slug = "custom_" + "".join(c if c.isalnum() else "_" for c in name.lower())[:40]
    # уникальность
    base = slug
    i = 1
    while await db.scalar(
        select(CompanyRole.id).where(CompanyRole.company_id == company.id, CompanyRole.slug == slug)
    ):
        slug = f"{base}_{i}"
        i += 1
    row = CompanyRole(
        company_id=company.id,
        name=name.strip()[:100],
        slug=slug,
        permissions=normalize_permissions(permissions),
        is_system=False,
    )
    db.add(row)
    await audit(
        db,
        company_id=company.id,
        user_id=user.id,
        action="role.create",
        details={"name": row.name, "slug": row.slug},
    )
    await db.flush()
    return row


async def update_custom_role(
    db: AsyncSession,
    user,
    role_id: int,
    *,
    name: str | None = None,
    permissions: dict | None = None,
) -> CompanyRole:
    company = await _company_for_roles(db, user)
    row = await db.get(CompanyRole, role_id)
    if not row or row.company_id != company.id:
        raise HTTPException(404, "Роль не найдена")
    if row.is_system:
        raise HTTPException(400, "Системные роли нельзя изменять")
    if name:
        row.name = name.strip()[:100]
    if permissions is not None:
        row.permissions = normalize_permissions(permissions)
    await audit(
        db,
        company_id=company.id,
        user_id=user.id,
        action="role.update",
        details={"role_id": role_id},
    )
    await db.flush()
    return row


async def delete_custom_role(db: AsyncSession, user, role_id: int) -> None:
    company = await _company_for_roles(db, user)
    row = await db.get(CompanyRole, role_id)
    if not row or row.company_id != company.id:
        raise HTTPException(404, "Роль не найдена")
    if row.is_system:
        raise HTTPException(400, "Системные роли нельзя удалить")
    used = await db.scalar(select(CompanyMember.id).where(CompanyMember.role_id == role_id).limit(1))
    if used:
        raise HTTPException(400, "Роль назначена сотрудникам — сначала смените роль")
    await db.delete(row)
    await audit(
        db,
        company_id=company.id,
        user_id=user.id,
        action="role.delete",
        details={"role_id": role_id},
    )
    await db.flush()


async def resolve_permissions(db: AsyncSession, company_id: int, user_id: int) -> dict[str, bool]:
    """Эффективные права участника (role_id → permissions, иначе slug из role string)."""
    from app.models import Company
    from app.services.company_policies import apply_policy_to_permissions, policies_for_company

    company = await db.get(Company, company_id)
    if company and company.owner_id == user_id:
        return merge_system("owner")
    m = await get_membership(db, company_id, user_id)
    if not m:
        return {k: False for k in PERMISSION_KEYS}
    if m.role_id:
        role = await db.get(CompanyRole, m.role_id)
        if role:
            perms = normalize_permissions(role.permissions)
            return apply_policy_to_permissions(
                perms, role_slug=role.slug or m.role or "", policies=policies_for_company(company)
            )
    slug = (m.role or "viewer").lower()
    if slug in SYSTEM_ROLE_PERMS:
        perms = merge_system(slug)
    else:
        perms = merge_system("viewer")
    return apply_policy_to_permissions(perms, role_slug=slug, policies=policies_for_company(company))


async def require_permission(
    db: AsyncSession,
    *,
    company_id: int,
    user_id: int,
    permission: str,
) -> None:
    if permission not in PERMISSION_KEYS:
        raise HTTPException(500, f"unknown permission {permission}")
    perms = await resolve_permissions(db, company_id, user_id)
    if not perms.get(permission):
        raise HTTPException(403, f"Нет права: {permission}")


async def assign_role_to_member(
    db: AsyncSession,
    actor,
    target_user_id: int,
    *,
    role_id: int | None = None,
    role_slug: str | None = None,
) -> CompanyMember:
    company = await _company_for_roles(db, actor)
    await ensure_system_roles(db, company.id)
    m = await get_membership(db, company.id, target_user_id)
    if not m:
        raise HTTPException(404, "Участник не найден")
    if target_user_id == company.owner_id:
        raise HTTPException(400, "Роль Owner не меняется")

    role: CompanyRole | None = None
    if role_id:
        role = await db.get(CompanyRole, role_id)
    elif role_slug:
        role = await db.scalar(
            select(CompanyRole).where(
                CompanyRole.company_id == company.id,
                CompanyRole.slug == role_slug,
            )
        )
    if not role or role.company_id != company.id:
        raise HTTPException(400, "Роль не найдена")
    if role.slug == "owner":
        raise HTTPException(400, "Нельзя назначить Owner")

    old = m.role
    m.role_id = role.id
    m.role = role.slug  # совместимость со старым кодом
    await audit(
        db,
        company_id=company.id,
        user_id=actor.id,
        action="member.role",
        details={"user_id": target_user_id, "from": old, "to": role.slug, "role_id": role.id},
    )
    await db.flush()
    return m
