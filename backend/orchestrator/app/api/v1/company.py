"""Корпоративные функции: команда, приглашения, API-ключи, съёмка по ссылке."""

from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_db_user, get_current_db_user_optional
from app.models import Company, CompanyInvitation, CompanyMember, Order, ShootLink, Transaction, User
from app.schemas.balance_filters import CompanyBalanceFilterPresetBody, CompanyBalanceFiltersBody
from app.services import api_keys as api_keys_svc
from app.services import pii as pii_svc
from app.services import photos as photos_service
from app.services import tariffs as tariff_svc
from app.services import upsells as upsell_svc
from app.services.queue import queue_service

router = APIRouter()


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="photographer", max_length=50)
    role_id: int | None = None
    company_id: int | None = None
    max_concurrent_orders: int | None = Field(default=3, ge=1, le=50)
    monthly_spending_limit: int | None = Field(default=None, ge=0)
    ttl_days: int = Field(default=7, ge=1, le=30)
    allowed_categories: list[str] | None = None


class ShootLinkRequest(BaseModel):
    task_uuid: str | None = None
    company_id: int | None = None
    category: str = "other"
    tier: str = "small"
    ttl_hours: int = Field(default=48, ge=1, le=168)
    max_uses: int = Field(default=1, ge=1, le=10)


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    scopes: list[str] = Field(default_factory=lambda: ["order:create", "order:read"])
    rate_limit_per_min: int = Field(default=1000, ge=10, le=10000)
    daily_limit: int | None = Field(default=None, ge=100, le=10_000_000)


class BulkOrderItem(BaseModel):
    task_uuid: str
    category: str = "other"
    tier: str = "small"
    photos_prefix: str | None = None
    upsell_options: list[str] = Field(default_factory=list)
    scale_calibration: dict | None = None


class BulkOrdersRequest(BaseModel):
    items: list[BulkOrderItem] = Field(min_length=1, max_length=100)


@router.get("/mine")
async def list_my_companies(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Компании пользователя: владение + членство (§3.14)."""
    owned = (await db.scalars(select(Company).where(Company.owner_id == user.id))).all()
    memberships = (
        await db.scalars(select(CompanyMember).where(CompanyMember.user_id == user.id))
    ).all()
    member_ids = {m.company_id for m in memberships}
    member_companies = []
    if member_ids:
        member_companies = (
            await db.scalars(select(Company).where(Company.id.in_(member_ids)))
        ).all()
    by_id: dict[int, Company] = {c.id: c for c in [*owned, *member_companies]}
    role_by_company = {m.company_id: m.role for m in memberships}
    for c in owned:
        role_by_company.setdefault(c.id, "owner")
    from app.services.company_roles import resolve_permissions
    from app.services.company_policies import extract_policies

    items = []
    for cid, c in by_id.items():
        perms = await resolve_permissions(db, cid, user.id)
        policies = extract_policies(c.settings)
        items.append(
            {
                "id": c.id,
                "name": c.name,
                "inn": c.inn,
                "requisites": (c.settings or {}).get("requisites") or {},
                "balance": c.balance if perms.get("can_view_finance") else None,
                "role": role_by_company.get(cid, "member"),
                "is_owner": c.owner_id == user.id,
                "permissions": perms,
                "e2e_photo_encryption": bool(policies.get("e2e_photo_encryption")),
            }
        )
    items.sort(key=lambda x: x["id"])
    return {"items": items}


@router.post("/invite")
async def invite_member(
    body: InviteRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Пригласить сотрудника (email, роль, лимиты)."""
    from app.services.access import require_company_permission
    from app.services.company_owner_2fa import require_owner_2fa_if_needed

    await require_owner_2fa_if_needed(user=user, db=db)
    company_id = body.company_id
    if company_id is None:
        owned = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
        if owned:
            company_id = owned.id
        else:
            # физлицо без компании — создаём personal workspace-приглашение без company
            company_id = None

    if company_id is not None:
        await require_company_permission(db, user, company_id, "can_invite_members")

    token = secrets.token_urlsafe(24)
    inv = CompanyInvitation(
        token=token,
        company_id=company_id,
        inviter_id=user.id,
        email=body.email.lower().strip(),
        role=body.role,
        max_concurrent_orders=body.max_concurrent_orders,
        monthly_spending_limit=body.monthly_spending_limit,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=body.ttl_days),
        meta={"allowed_categories": body.allowed_categories} if body.allowed_categories else {},
    )
    db.add(inv)
    await db.flush()
    from app.models import AuditLog

    db.add(
        AuditLog(
            company_id=company_id,
            user_id=user.id,
            action="company_invite_sent",
            details={
                "invited_email": inv.email,
                "role": inv.role,
                "max_concurrent_orders": inv.max_concurrent_orders,
                "monthly_spending_limit": inv.monthly_spending_limit,
                "invitation_id": inv.id,
                "invited_by_user_id": user.id,
            },
        )
    )
    try:
        from app.services import company_webhooks as wh

        await wh.emit(
            db,
            company_id=company_id,
            event="member.invited",
            payload={
                "invitation_id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "inviter_id": user.id,
            },
        )
    except Exception:  # noqa: BLE001
        pass
    await db.commit()
    await db.refresh(inv)
    url = f"{settings.SELLER_PUBLIC_URL.rstrip('/')}/invite/{token}"
    return {
        "id": inv.id,
        "token": token,
        "email": inv.email,
        "role": inv.role,
        "url": url,
        "expires_at": inv.expires_at.isoformat(),
        "status": inv.status,
        "company_id": company_id,
    }


@router.get("/invitations")
async def list_invitations(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(
            select(CompanyInvitation)
            .where(CompanyInvitation.inviter_id == user.id)
            .order_by(CompanyInvitation.id.desc())
            .limit(100)
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "email": r.email,
                "role": r.role,
                "status": r.status,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "url": f"{settings.SELLER_PUBLIC_URL.rstrip('/')}/invite/{r.token}",
            }
            for r in rows
        ]
    }


@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Отмена pending-приглашения §2.5.5."""
    from app.services.access import require_company_permission

    inv = await db.get(CompanyInvitation, invitation_id)
    if not inv:
        raise HTTPException(404, "Не найдено")
    await require_company_permission(db, user, inv.company_id, "can_invite_members")
    if inv.status != "pending":
        raise HTTPException(400, "Приглашение уже обработано")
    inv.status = "revoked"
    await db.commit()
    return {"message": "ok", "id": invitation_id}


@router.get("/invite/{token}")
async def get_invitation(token: str, db: AsyncSession = Depends(get_db)):
    inv = await db.scalar(select(CompanyInvitation).where(CompanyInvitation.token == token))
    if not inv:
        raise HTTPException(404, "Приглашение не найдено")
    exp = inv.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if inv.status != "pending" or exp < datetime.now(timezone.utc):
        raise HTTPException(410, "Приглашение недействительно")
    return {
        "email": inv.email,
        "role": inv.role,
        "company_id": inv.company_id,
        "expires_at": inv.expires_at.isoformat(),
    }


@router.post("/invite/{token}/accept")
async def accept_invitation(
    token: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await db.scalar(select(CompanyInvitation).where(CompanyInvitation.token == token))
    if not inv or inv.status != "pending":
        raise HTTPException(404, "Приглашение не найдено")
    exp = inv.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        inv.status = "expired"
        await db.commit()
        raise HTTPException(410, "Срок приглашения истёк")
    if user.email.lower() != inv.email.lower():
        raise HTTPException(403, "Войдите под email из приглашения")

    company_id = inv.company_id
    if not company_id:
        meta = inv.meta or {}
        imp = meta.get("import_company")
        if imp and inv.role == "owner":
            dup = await db.scalar(select(Company).where(Company.inn == imp.get("inn")))
            if dup:
                raise HTTPException(400, "Компания с таким ИНН уже существует")
            company = Company(
                name=str(imp.get("name") or "Company"),
                inn=str(imp.get("inn") or ""),
                owner_id=user.id,
                status="active",
                settings=pii_svc.encrypt_company_settings(
                    {"kpp": imp.get("kpp"), "ogrn": imp.get("ogrn")}
                ),
            )
            db.add(company)
            await db.flush()
            company_id = company.id
            inv.company_id = company_id
            db.add(CompanyMember(company_id=company.id, user_id=user.id, role="owner"))
            user.account_type = "legal"
            user.status = "active_legal"

    if company_id:
        existing = await db.scalar(
            select(CompanyMember).where(
                CompanyMember.company_id == company_id,
                CompanyMember.user_id == user.id,
            )
        )
        if not existing:
            inv_meta = inv.meta or {}
            allowed_cats = inv_meta.get("allowed_categories")
            db.add(
                CompanyMember(
                    company_id=company_id,
                    user_id=user.id,
                    role=inv.role,
                    max_concurrent_orders=inv.max_concurrent_orders,
                    monthly_spending_limit=inv.monthly_spending_limit,
                    allowed_categories=allowed_cats if isinstance(allowed_cats, list) else None,
                )
            )
            from app.models import AuditLog

            db.add(
                AuditLog(
                    company_id=company_id,
                    user_id=user.id,
                    action="company_member_joined",
                    details={
                        "invitation_id": inv.id,
                        "role": inv.role,
                        "email": user.email,
                    },
                )
            )
    inv.status = "accepted"
    await db.commit()
    return {"ok": True, "role": inv.role, "company_id": inv.company_id}


@router.get("/tariffs")
async def company_tariffs(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Эффективные тарифы компании с персональными ценами §8.2."""
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    items = await tariff_svc.list_tariffs(db)
    out = []
    for item in items:
        if item["code"] not in ("small", "large", "import_glb"):
            continue
        base = item["amount_rub"]
        effective = await tariff_svc.get_amount_for_company(db, item["code"], company)
        out.append(
            {
                **item,
                "base_amount_rub": base,
                "amount_rub": effective,
                "has_override": effective != base,
            }
        )
    return {"company_id": company.id, "items": out}


@router.post("/delete-request")
async def request_company_deletion(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Запрос удаления компании (grace 30 дней) §9.8."""
    from app.services.company_deletion import request_deletion
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    out = await request_deletion(db, company, user_id=user.id)
    await db.commit()
    return out


@router.post("/delete-cancel")
async def cancel_company_deletion(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Отмена запланированного удаления компании §9.8."""
    from app.services.company_deletion import cancel_deletion
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    out = await cancel_deletion(db, company, user_id=user.id)
    await db.commit()
    return out


@router.get("/backup-insurance/status")
async def company_backup_insurance_status(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Покрытие страхующих копий B2B §9.9."""
    from app.services.backup_insurance import company_backup_status
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    return await company_backup_status(db, company.id)


@router.get("/members")
async def list_members(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(default=None, max_length=120),
    role: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    from app.services.company_members import require_manager

    company, _role = await require_manager(db, user)
    where = [CompanyMember.company_id == company.id]
    if role and role.strip():
        where.append(CompanyMember.role == role.strip())
    stmt = select(CompanyMember).where(*where)
    if search and search.strip():
        q = f"%{search.strip()}%"
        stmt = stmt.join(User, User.id == CompanyMember.user_id).where(
            or_(User.email.ilike(q), User.full_name.ilike(q))
        )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    members = (await db.scalars(stmt.order_by(CompanyMember.id).offset(offset).limit(limit))).all()
    from app.models import Order

    active_statuses = ("pending", "awaiting_payment", "paid", "queued", "processing", "generating")
    items = []
    for m in members:
        u = await db.get(User, m.user_id)
        active_count = await db.scalar(
            select(func.count()).select_from(Order).where(
                Order.company_id == company.id,
                Order.user_id == m.user_id,
                Order.status.in_(active_statuses),
            )
        )
        last_at = await db.scalar(
            select(func.max(Order.created_at)).where(
                Order.company_id == company.id,
                Order.user_id == m.user_id,
            )
        )
        items.append(
            {
                "user_id": m.user_id,
                "email": u.email if u else None,
                "full_name": u.full_name if u else None,
                "role": m.role,
                "max_concurrent_orders": m.max_concurrent_orders,
                "monthly_spending_limit": m.monthly_spending_limit,
                "active_orders_count": int(active_count or 0),
                "last_activity_at": last_at.isoformat() if last_at else None,
            }
        )
    return {
        "items": items,
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "company_id": company.id,
    }


@router.get("/members/{user_id}")
async def get_member(
    user_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.company_members import require_manager

    company, _role = await require_manager(db, user)
    m = await db.scalar(
        select(CompanyMember).where(
            CompanyMember.company_id == company.id,
            CompanyMember.user_id == user_id,
        )
    )
    if not m:
        raise HTTPException(404, "Сотрудник не найден")
    u = await db.get(User, m.user_id)
    return {
        "user_id": m.user_id,
        "email": u.email if u else None,
        "full_name": u.full_name if u else None,
        "role": m.role,
        "max_concurrent_orders": m.max_concurrent_orders,
        "monthly_spending_limit": m.monthly_spending_limit,
        "allowed_categories": m.allowed_categories,
        "company_id": company.id,
    }


@router.delete("/members/{user_id}")
async def remove_member(
    user_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_members as cm

    await cm.remove_member(db, user, user_id)
    await db.commit()
    return {"ok": True}


@router.post("/members/{user_id}/reset-password")
async def reset_member_password(
    user_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """§20.5 — Owner/Manager: ссылка сброса пароля на email сотрудника."""
    from app.services import company_members as cm
    from app.services.auth import request_password_reset

    company, _role = await cm.require_manager(db, user)
    m = await cm.get_membership(db, company.id, user_id)
    if not m:
        raise HTTPException(404, "Участник не найден")
    target = await db.get(User, user_id)
    if not target or not target.email:
        raise HTTPException(404, "Пользователь не найден")
    await request_password_reset(db, target.email)
    await cm.audit(
        db,
        company_id=company.id,
        user_id=user.id,
        action="member_password_reset",
        details={"target_user_id": user_id},
    )
    await db.commit()
    return {"ok": True, "message": "Ссылка для сброса пароля отправлена на email"}


class CompanyRequisitesBody(BaseModel):
    inn: str | None = Field(default=None, max_length=12)
    legal_name: str | None = Field(default=None, max_length=255)
    legal_address: str | None = None
    bank_name: str | None = None
    bank_bik: str | None = Field(default=None, max_length=9)
    bank_account: str | None = Field(default=None, max_length=20)


@router.patch("/requisites")
async def update_company_requisites(
    body: CompanyRequisitesBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """§20.8 — реквизиты компании (только Owner)."""
    company = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
    if not company:
        raise HTTPException(403, "Только Owner компании")
    payload = body.model_dump(exclude_unset=True)
    if "inn" in payload and payload["inn"] is not None:
        company.inn = payload.pop("inn")
    if payload:
        settings = dict(company.settings or {})
        req = dict(settings.get("requisites") or {})
        req.update(payload)
        settings["requisites"] = req
        company.settings = settings
    await db.commit()
    req_out = dict((company.settings or {}).get("requisites") or {})
    return {"inn": company.inn, **req_out}


class RoleBody(BaseModel):
    role: str | None = None
    role_id: int | None = None


@router.patch("/members/{user_id}/role")
async def change_role(
    user_id: int,
    body: RoleBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_roles as cr

    m = await cr.assign_role_to_member(
        db, user, user_id, role_id=body.role_id, role_slug=body.role
    )
    await db.commit()
    return {"user_id": m.user_id, "role": m.role, "role_id": m.role_id}


class CustomRoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    permissions: dict = Field(default_factory=dict)


class CustomRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    permissions: dict | None = None


@router.get("/roles")
async def list_company_roles(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_roles as cr
    from app.services.access import company_for_permission
    from app.services.permissions import PERMISSION_KEYS

    await company_for_permission(db, user, "can_manage_roles")
    items = await cr.list_roles(db, user)
    await db.commit()
    return {"items": items, "permission_keys": list(PERMISSION_KEYS)}


@router.post("/roles")
async def create_company_role(
    body: CustomRoleCreate,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_roles as cr
    from app.services.access import company_for_permission

    await company_for_permission(db, user, "can_manage_roles")
    row = await cr.create_custom_role(db, user, name=body.name, permissions=body.permissions)
    await db.commit()
    return {"id": row.id, "name": row.name, "slug": row.slug, "permissions": row.permissions}


@router.patch("/roles/{role_id}")
async def update_company_role(
    role_id: int,
    body: CustomRoleUpdate,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_roles as cr
    from app.services.access import company_for_permission

    await company_for_permission(db, user, "can_manage_roles")
    row = await cr.update_custom_role(
        db, user, role_id, name=body.name, permissions=body.permissions
    )
    await db.commit()
    return {"id": row.id, "name": row.name, "permissions": row.permissions}


@router.delete("/roles/{role_id}")
async def delete_company_role(
    role_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_roles as cr
    from app.services.access import company_for_permission

    await company_for_permission(db, user, "can_manage_roles")
    await cr.delete_custom_role(db, user, role_id)
    await db.commit()
    return {"ok": True}


class LimitsBody(BaseModel):
    max_concurrent_orders: int | None = Field(default=None, ge=1, le=100)
    monthly_spending_limit: int | None = Field(default=None, ge=0)
    allowed_categories: list[str] | None = None


@router.patch("/members/{user_id}/limits")
async def change_limits(
    user_id: int,
    body: LimitsBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_members as cm

    m = await cm.change_limits(
        db,
        user,
        user_id,
        max_concurrent_orders=body.max_concurrent_orders,
        monthly_spending_limit=body.monthly_spending_limit,
        allowed_categories=body.allowed_categories,
    )
    await db.commit()
    return {
        "user_id": m.user_id,
        "max_concurrent_orders": m.max_concurrent_orders,
        "monthly_spending_limit": m.monthly_spending_limit,
        "allowed_categories": m.allowed_categories,
    }


@router.get("/members/{user_id}/tasks")
async def member_tasks(
    user_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_members as cm

    items = await cm.member_tasks(db, user, user_id)
    await db.commit()
    return {"items": items}


@router.get("/publication-funnel")
async def company_publication_funnel(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    export: bool = Query(False),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Воронка публикации по сотрудникам §7.9.2 (Owner)."""
    from app.services import publication_funnel as funnel_svc
    from app.services.company_members import get_owned_company
    from fastapi.responses import Response

    company = await get_owned_company(db, user)
    data = await funnel_svc.team_funnel(
        db,
        company_id=company.id,
        date_from=date_from,
        date_to=date_to,
    )
    await db.commit()
    if export:
        body = funnel_svc.team_funnel_to_csv(data)
        return Response(
            content=body,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="team-publication-funnel.csv"'},
        )
    return data


@router.get("/settings")
async def get_settings(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_policies as pol

    return await pol.get_policies(db, user)


class PoliciesBody(BaseModel):
    policies: dict | None = None
    settings: dict | None = None
    notification_routing: dict[str, str] | None = None
    default_max_concurrent_orders: int | None = Field(default=None, ge=1, le=20)
    default_monthly_spending_limit: int | None = Field(default=None, ge=0)
    default_allowed_categories: list[str] | None = None
    allow_photographer_download: bool | None = None
    allow_photographer_add_links: bool | None = None
    require_2fa_for_all: bool | None = None
    auto_block_inactive_days: int | None = Field(default=None, ge=1, le=3650)
    low_balance_threshold: int | None = Field(default=None, ge=0)
    force_trellis_version: str | None = None


@router.patch("/settings")
async def update_settings(
    body: PoliciesBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить глобальные политики доступа (§2.5.4) — структурированные поля."""
    from app.services import company_policies as pol

    flat = body.model_dump(exclude_none=True)
    result = await pol.update_policies(db, user, flat)
    await db.commit()
    return result


@router.get("/policies")
async def get_policies(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_policies as pol

    return await pol.get_policies(db, user)


@router.patch("/policies")
async def patch_policies(
    body: PoliciesBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_policies as pol

    result = await pol.update_policies(db, user, body.model_dump(exclude_none=True))
    await db.commit()
    return result


@router.get("/members/{member_id}/sessions")
async def member_sessions(
    member_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_members as cm

    items = await cm.list_sessions(db, user, member_id)
    await db.commit()
    return {"items": items}


@router.post("/members/{member_id}/sessions/revoke")
async def revoke_sessions(
    member_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_members as cm

    n = await cm.revoke_sessions(db, user, member_id)
    await db.commit()
    return {"revoked": n}


@router.get("/audit")
async def audit_log(
    action: str | None = Query(None),
    action_prefix: str | None = Query(None, description="Например oauth_"),
    user_id: int | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    ip: str | None = Query(None, max_length=64),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import audit_query as aq
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    member_ids = list(
        await db.scalars(select(CompanyMember.user_id).where(CompanyMember.company_id == company.id))
    )
    return await aq.list_company_audit_logs(
        db,
        company_id=company.id,
        member_user_ids=member_ids,
        action=action,
        action_prefix=action_prefix,
        user_id=user_id,
        days=days,
        date_from=date_from,
        date_to=date_to,
        ip=ip,
        limit=limit,
        offset=offset,
    )


@router.get("/access-log")
async def company_access_log(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    model_uuid: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Отчёт Owner по скачиваниям моделей компании §10.7.2."""
    from app.services import access_log as access_svc
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    return await access_svc.list_access_logs(
        db,
        company_id=company.id,
        model_uuid=model_uuid,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/access-log/export")
async def company_access_log_export(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    model_uuid: str | None = Query(None),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """CSV export скачиваний моделей компании §10.7.2."""
    from fastapi.responses import Response

    from app.services import access_log as access_svc
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    data = await access_svc.list_access_logs(
        db,
        company_id=company.id,
        model_uuid=model_uuid,
        date_from=date_from,
        date_to=date_to,
        limit=5000,
    )
    return Response(
        content=access_svc.to_csv(data["items"]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="company-access-log.csv"'},
    )


@router.get("/audit/export")
async def audit_export(
    action: str | None = Query(None),
    action_prefix: str | None = Query(None),
    user_id: int | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    ip: str | None = Query(None, max_length=64),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    import csv
    import io

    from fastapi.responses import Response

    from app.services import audit_query as aq
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    member_ids = list(
        await db.scalars(select(CompanyMember.user_id).where(CompanyMember.company_id == company.id))
    )
    data = await aq.list_company_audit_logs(
        db,
        company_id=company.id,
        member_user_ids=member_ids,
        action=action,
        action_prefix=action_prefix,
        user_id=user_id,
        days=days,
        date_from=date_from,
        date_to=date_to,
        ip=ip,
        limit=5000,
        offset=0,
    )
    rows = data["items"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "user_id", "action", "ip_address", "details", "created_at"])
    for r in rows:
        w.writerow([r["id"], r["user_id"], r["action"], r.get("ip_address") or "", r["details"], r["created_at"] or ""])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit.csv"'},
    )


@router.get("/user-events/export")
async def company_user_events_export(
    days: int = Query(30, ge=1, le=365),
    event_type: str | None = Query(None, max_length=64),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Экспорт user_events компании §12.7."""
    from fastapi.responses import Response

    from app.services import user_events as ue
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    body = await ue.export_csv(
        db,
        company_id=company.id,
        days=days,
        event_type=event_type,
    )
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="company-user-events.csv"'},
    )


@router.get("/balance")
async def company_balance(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_balance as bal

    data = await bal.get_balance(db, user)
    await db.commit()
    return data


class TopupBody(BaseModel):
    amount: int = Field(ge=100, le=10_000_000)
    payment_method: str = Field(default="redirect", pattern=r"^(redirect|sbp_qr|card|sbp|manual)$")
    note: str | None = None
    customer_name: str | None = None


@router.post("/balance/topup")
async def company_topup(
    body: TopupBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Пополнение Company.balance через ЮKassa (карта/СБП) или manual (§8.7)."""
    from app.core.config import settings
    from app.services import company_balance as bal
    from app.services.company_owner_2fa import require_owner_2fa_if_needed
    from app.services.tax import build_receipt_for_payment
    from app.services.yookassa import yookassa_service

    await require_owner_2fa_if_needed(user=user, db=db)

    method = body.payment_method
    if method == "manual":
        data = await bal.topup_manual(db, user, body.amount, body.note)
        await db.commit()
        return {**data, "payment_method": "manual"}

    if method == "card":
        method = "redirect"
    if method == "sbp":
        method = "sbp_qr"

    company = await bal.get_owned_company_row(db, user)
    description = f"Пополнение баланса компании #{company.id}"
    receipt = await build_receipt_for_payment(
        db,
        customer_email=user.email,
        description=description,
        amount_rub=body.amount,
        customer_name=body.customer_name or user.full_name or company.name,
    )
    payment = await yookassa_service.create_payment(
        body.amount,
        description,
        return_url=f"{settings.SELLER_PUBLIC_URL}/balance",
        metadata={
            "purpose": "company_topup",
            "user_id": str(user.id),
            "company_id": str(company.id),
            "amount": str(body.amount),
            "payment_method": method,
        },
        payment_method=method,  # type: ignore[arg-type]
        receipt=receipt,
        idempotence_key=f"company-topup-{company.id}-{body.amount}-{method}",
    )
    from app.services import pending_payments as pend

    await pend.upsert_pending(
        db,
        payment_id=payment["id"],
        user_id=user.id,
        company_id=company.id,
        amount=body.amount,
        payment_method=method,
        purpose="company_topup",
    )
    await db.commit()
    return {
        "company_id": company.id,
        "payment_id": payment["id"],
        "status": payment["status"],
        "confirmation_url": payment.get("confirmation_url"),
        "confirmation_data": payment.get("confirmation_data"),
        "confirmation_type": payment.get("confirmation_type"),
        "payment_method": method,
        "amount": body.amount,
        "receipt": True,
    }


@router.get("/balance/payment/{payment_id}")
async def company_topup_payment_status(
    payment_id: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Polling статуса пополнения компании (СБП QR) §20.3.3."""
    from app.core.config import settings
    from app.services import company_balance as bal
    from app.services.yookassa import yookassa_service

    company = await bal.get_owned_company_row(db, user)
    if payment_id.startswith("dev-"):
        await db.refresh(company)
        return {
            "status": "succeeded",
            "payment_id": payment_id,
            "company_balance": company.balance,
            "dev_mock": True,
        }
    if not yookassa_service.configured:
        if settings.is_development:
            await db.refresh(company)
            return {"status": "pending", "payment_id": payment_id, "company_balance": company.balance}
        raise HTTPException(503, "ЮKassa не настроена")

    payment = await yookassa_service.get_payment(payment_id)
    meta = payment.get("metadata") or {}
    if str(meta.get("user_id")) != str(user.id) or str(meta.get("company_id")) != str(company.id):
        raise HTTPException(403, "Платёж принадлежит другому пользователю")
    await db.refresh(company)
    tx = await db.scalar(select(Transaction).where(Transaction.external_id == payment_id))
    status = payment.get("status") or "pending"
    if tx or status == "succeeded":
        status = "succeeded"
    elif status == "canceled":
        from app.services import pending_payments as pend

        await pend.mark_status(db, payment_id, "canceled")
        await db.commit()
    return {
        "status": status,
        "payment_id": payment_id,
        "company_balance": company.balance,
        "amount": int(float((payment.get("amount") or {}).get("value") or 0)),
    }


@router.get("/transactions")
async def company_transactions(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Query(default=None, description="Фильтр по сотруднику §8"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    tx_type: str = Query(default="all", alias="type", pattern=r"^(all|topup|charge|refund)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    from app.services import company_balance as bal
    from app.services import pending_payments as pend
    from app.services.access import company_for_permission

    company = await company_for_permission(db, user, "can_view_finance")
    await bal.validate_company_tx_user_filter(db, company=company, actor=user, user_id=user_id)
    stmt = bal.build_company_tx_stmt(
        company.id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    tx_total = await bal.count_company_transactions(
        db,
        company.id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    pending_items = await pend.list_pending_dicts(
        db,
        company_id=company.id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    pending_count = len(pending_items)
    total = int(tx_total) + pending_count

    if offset < pending_count:
        tx_offset = 0
        tx_limit = max(0, limit - (pending_count - offset))
    else:
        tx_offset = offset - pending_count
        tx_limit = limit

    rows = (await db.scalars(stmt.offset(tx_offset).limit(tx_limit))).all()
    tx_items = [bal.transaction_to_dict(t, include_user=True) for t in rows]

    if offset < pending_count:
        page = pending_items[offset : offset + limit]
        need = limit - len(page)
        if need > 0:
            page.extend(tx_items[:need])
    else:
        page = tx_items

    return {
        "company_id": company.id,
        "items": page,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/transactions/export")
async def export_company_transactions(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Query(default=None, description="Фильтр по сотруднику §8"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    tx_type: str = Query(default="all", alias="type", pattern=r"^(all|topup|charge|refund)$"),
):
    """CSV выгрузка операций компании за период (can_view_finance §8)."""
    from fastapi.responses import Response

    from app.services import company_balance as bal
    from app.services.access import company_for_permission

    company = await company_for_permission(db, user, "can_view_finance")
    await bal.validate_company_tx_user_filter(db, company=company, actor=user, user_id=user_id)
    csv_body = await bal.export_company_transactions_csv(
        db,
        company=company,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="company_transactions.csv"'},
    )


@router.post("/data-export")
async def request_company_data_export(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """§9.5.2 — асинхронный экспорт всех данных компании (ZIP на email за 24ч)."""
    from app.services import company_data_export as cde_svc

    company = await api_keys_svc.require_company_owner(db, user)
    row = await cde_svc.request_export(db, company=company, user=user)
    await db.commit()

    from app.tasks.celery_app import process_company_data_export

    process_company_data_export.delay(row.id)
    return {
        "export_id": row.id,
        "status": row.status,
        "message": "Экспорт запущен. Ссылка придёт на email после формирования архива.",
    }


@router.get("/data-export/{export_id}")
async def get_company_data_export_status(
    export_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Статус экспорта данных компании §9.5.2."""
    from app.services import company_data_export as cde_svc

    company = await api_keys_svc.require_company_owner(db, user)
    row = await cde_svc.get_export(db, company_id=company.id, export_id=export_id)
    if not row:
        raise HTTPException(404, "Экспорт не найден")
    return cde_svc.export_to_dict(row)


@router.get("/balance-filters")
async def get_company_balance_filters(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Saved company transaction filters for Manager/Owner §8 / §20.3.4."""
    from app.services import balance_filters as bf
    from app.services.access import company_for_permission

    company = await company_for_permission(db, user, "can_view_finance")
    return {
        "scope": "company",
        "company_id": company.id,
        "filters": bf.get_company_filters(user, company.id),
    }


@router.put("/balance-filters")
async def put_company_balance_filters(
    body: CompanyBalanceFiltersBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist company transaction filters §8 / §20.3.4."""
    from app.services import balance_filters as bf
    from app.services.access import company_for_permission

    company = await company_for_permission(db, user, "can_view_finance")
    saved = await bf.save_company_filters(db, user, company.id, body.model_dump())
    await db.commit()
    return {"scope": "company", "company_id": company.id, "filters": saved}


@router.get("/balance-filter-presets")
async def get_company_balance_filter_presets(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import balance_filters as bf
    from app.services.access import company_for_permission

    company = await company_for_permission(db, user, "can_view_finance")
    return {
        "scope": "company",
        "company_id": company.id,
        "items": bf.list_presets(user, company_id=company.id),
    }


@router.post("/balance-filter-presets")
async def create_company_balance_filter_preset(
    body: CompanyBalanceFilterPresetBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import balance_filters as bf
    from app.services.access import company_for_permission

    company = await company_for_permission(db, user, "can_view_finance")
    try:
        row = await bf.upsert_preset(
            db,
            user,
            name=body.name,
            filters=body.model_dump(),
            company_id=company.id,
        )
    except ValueError as exc:
        if str(exc) == "limit":
            raise HTTPException(400, "Максимум 10 сохранённых представлений") from exc
        raise HTTPException(400, "Укажите название") from exc
    await db.commit()
    return {"scope": "company", "company_id": company.id, "preset": row}


@router.delete("/balance-filter-presets/{preset_id}")
async def delete_company_balance_filter_preset(
    preset_id: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import balance_filters as bf
    from app.services.access import company_for_permission

    company = await company_for_permission(db, user, "can_view_finance")
    ok = await bf.delete_preset(db, user, preset_id=preset_id, company_id=company.id)
    if not ok:
        raise HTTPException(404, "Представление не найдено")
    await db.commit()
    return {"ok": True}


class WebhookCreate(BaseModel):
    url: str
    events: list[str] = Field(default_factory=lambda: ["model.generated"])
    secret: str = Field(default="", max_length=128)


@router.post("/webhooks")
async def create_webhook(
    body: WebhookCreate,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_webhooks as wh

    row = await wh.create_webhook(db, user, url=body.url, events=body.events, secret=body.secret)
    await db.commit()
    return {"id": row.id, "url": row.url, "events": row.events}


@router.get("/webhooks")
async def list_webhooks(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_webhooks as wh

    items = await wh.list_webhooks(db, user)
    await db.commit()
    return {"items": items}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_webhooks as wh

    await wh.delete_webhook(db, user, webhook_id)
    await db.commit()
    return {"ok": True}


@router.get("/webhooks/deliveries")
async def webhook_deliveries(
    status: str | None = None,
    webhook_id: int | None = None,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Лог доставок + DLQ (§14.5.4). status=dlq|pending|delivered."""
    from app.services import company_webhooks as wh

    items = await wh.list_deliveries(db, user, status=status, webhook_id=webhook_id)
    return {"items": items}


@router.get("/webhooks/deliveries/dashboard")
async def webhook_deliveries_dashboard(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Сводка retries / DLQ для Owner (§14.5.4)."""
    from app.services import company_webhooks as wh
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    return await wh.delivery_dashboard(db, company_id=company.id)


@router.post("/webhooks/deliveries/replay-dlq")
async def webhook_replay_dlq(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Массовый replay DLQ (§14.5.4)."""
    from app.services import company_webhooks as wh

    result = await wh.replay_dlq(db, user)
    await db.commit()
    return result


@router.post("/webhooks/deliveries/{delivery_id}/retry")
async def webhook_delivery_retry(
    delivery_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_webhooks as wh

    result = await wh.retry_delivery(db, user, delivery_id)
    await db.commit()
    return result


@router.get("/webhooks/deliveries/{delivery_id}")
async def webhook_delivery_detail(
    delivery_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_webhooks as wh

    return await wh.get_delivery(db, user, delivery_id)


@router.post("/models/mass-extend-storage")
async def company_mass_extend_storage(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Owner: массовое продление хранения исходников §9.1.2."""
    from app.services import model_storage as ms
    from app.services.company_members import get_owned_company
    from app.services.company_owner_2fa import require_owner_2fa_if_needed

    await require_owner_2fa_if_needed(user=user, db=db)
    company = await get_owned_company(db, user)
    result = await ms.mass_extend_company_storage(db, company_id=company.id, user=user)
    await db.commit()
    return result


class CompanyMarketplaceCredentialBody(BaseModel):
    marketplace: str = Field(pattern=r"^(wb|ozon|wildberries)$")
    api_key: str = Field(min_length=8, max_length=512)
    client_id: str | None = Field(default=None, max_length=64)
    enabled: bool = True


@router.get("/marketplace/status")
async def company_marketplace_status(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Статус API-публикации для seller UI §7.6."""
    from app.models import MarketplaceCredential
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    creds = (
        await db.scalars(
            select(MarketplaceCredential).where(
                MarketplaceCredential.company_id == company.id,
                MarketplaceCredential.enabled.is_(True),
            )
        )
    ).all()
    global_creds = (
        await db.scalars(
            select(MarketplaceCredential).where(
                MarketplaceCredential.company_id.is_(None),
                MarketplaceCredential.enabled.is_(True),
            )
        )
    ).all()
    have = {c.marketplace for c in creds} | {c.marketplace for c in global_creds}
    return {
        "upload_enabled": settings.MARKETPLACE_UPLOAD_ENABLED,
        "company_id": company.id,
        "credentials": {
            "wb": "wb" in have,
            "ozon": "ozon" in have,
        },
        "company_keys_count": len(creds),
    }


@router.get("/marketplace/credentials")
async def company_list_marketplace_credentials(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Owner: WB/Ozon API-ключи компании §7.6 / §14.6."""
    from app.models import MarketplaceCredential
    from app.services import marketplace_upload as mp_svc
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    rows = (
        await db.scalars(
            select(MarketplaceCredential)
            .where(MarketplaceCredential.company_id == company.id)
            .order_by(MarketplaceCredential.marketplace)
        )
    ).all()
    return {
        "upload_enabled": settings.MARKETPLACE_UPLOAD_ENABLED,
        "items": [mp_svc.credential_public(r) for r in rows],
    }


@router.put("/marketplace/credentials")
async def company_upsert_marketplace_credentials(
    body: CompanyMarketplaceCredentialBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Owner: сохранить WB/Ozon API-ключ компании §7.6 / §14.6."""
    from app.models import AuditLog
    from app.services import marketplace_upload as mp_svc
    from app.services.company_members import get_owned_company
    from app.services.company_owner_2fa import require_owner_2fa_if_needed

    await require_owner_2fa_if_needed(user=user, db=db)
    company = await get_owned_company(db, user)
    row = await mp_svc.upsert_credential(
        db,
        marketplace=body.marketplace,
        api_key=body.api_key,
        company_id=company.id,
        client_id=body.client_id,
        enabled=body.enabled,
    )
    db.add(
        AuditLog(
            company_id=company.id,
            user_id=user.id,
            action="marketplace_credential.upsert",
            details={"marketplace": row.marketplace, "enabled": row.enabled},
        )
    )
    await db.commit()
    return mp_svc.credential_public(row)


@router.post("/shoot_link")
async def create_shoot_link(
    body: ShootLinkRequest | None = None,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать одноразовую ссылку для внешнего фотографа."""
    from app.services.access import require_company_permission
    from app.services.company_owner_2fa import require_owner_2fa_if_needed

    await require_owner_2fa_if_needed(user=user, db=db)
    payload = body or ShootLinkRequest()
    company_id = payload.company_id
    if company_id is None:
        owned = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
        company_id = owned.id if owned else None
    if company_id is not None:
        await require_company_permission(db, user, company_id, "can_invite_members")
    from app.services import shoot_link_limits as sll

    await sll.assert_can_create(db, company_id=company_id)
    task_uuid = payload.task_uuid or str(uuid.uuid4())
    token = secrets.token_urlsafe(24)
    link = ShootLink(
        token=token,
        task_uuid=task_uuid,
        user_id=user.id,
        company_id=company_id,
        category=payload.category,
        tier=payload.tier,
        status="active",
        max_uses=payload.max_uses,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=payload.ttl_hours),
    )
    db.add(link)
    await db.commit()
    url = f"{settings.SELLER_PUBLIC_URL.rstrip('/')}/shoot/{token}"
    return {
        "token": token,
        "task_uuid": task_uuid,
        "url": url,
        "expires_at": link.expires_at.isoformat(),
        "photos_prefix": f"photos/{task_uuid}/",
    }


@router.get("/shoot_links/stats")
async def shoot_links_stats(
    company_id: int | None = None,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Статистика съёмки по ссылке для Owner/Manager (§3.15.4)."""
    from app.services import shoot_links as shoot_svc
    from app.services.access import require_company_permission

    cid = company_id
    if cid is None:
        owned = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
        cid = owned.id if owned else None
    if cid is None:
        raise HTTPException(400, "Укажите company_id")
    await require_company_permission(db, user, cid, "can_invite_members")
    data = await shoot_svc.company_stats(db, cid)
    await db.commit()
    return data


@router.post("/api_keys")
async def create_api_key(
    body: ApiKeyCreate,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    row, plain = await api_keys_svc.create_key(
        db,
        user=user,
        name=body.name,
        scopes=body.scopes,
        rate_limit_per_min=body.rate_limit_per_min,
        daily_limit=body.daily_limit,
    )
    await db.commit()
    return {
        "id": row.id,
        "name": row.name,
        "key": plain,
        "key_prefix": row.key_prefix,
        "scopes": row.scopes,
        "rate_limit_per_min": row.rate_limit_per_min,
        "daily_limit": row.daily_limit,
        "warning": "Ключ показывается один раз",
    }


@router.get("/api_keys")
async def list_api_keys(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    items = await api_keys_svc.list_keys(db, user)
    await db.commit()
    return {"items": items, "allowed_scopes": sorted(api_keys_svc.ALLOWED_SCOPES)}


@router.delete("/api_keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    await api_keys_svc.revoke_key(db, user, key_id)
    await db.commit()
    return {"ok": True}


@router.post("/orders/bulk")
async def bulk_orders(
    body: BulkOrdersRequest,
    request: Request,
    user: User | None = Depends(get_current_db_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """До 100 заказов; JWT Owner или X-API-Key scope order:create."""
    api_key_header = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    company = None
    actor: User | None = user
    if api_key_header:
        key_row, company, owner = await api_keys_svc.authenticate_api_key(db, api_key_header)
        if "order:create" not in (key_row.scopes or []):
            raise HTTPException(403, "Нужен scope order:create")
        actor = owner
    else:
        if not actor:
            raise HTTPException(401, "Требуется JWT или X-API-Key")
        company = await api_keys_svc.require_company_owner(db, actor)

    created = []
    errors = []
    for item in body.items:
        try:
            existing = await db.scalar(select(Order).where(Order.task_uuid == item.task_uuid))
            if existing:
                created.append(
                    {
                        "task_uuid": item.task_uuid,
                        "id": existing.id,
                        "status": existing.status,
                        "idempotent": True,
                    }
                )
                continue
            try:
                photos_service.require_all_photos(item.task_uuid)
            except HTTPException:
                errors.append({"task_uuid": item.task_uuid, "error": "Нужны 12 фото в MinIO"})
                continue
            base = await tariff_svc.get_amount_for_company(db, item.tier, company)
            codes, upsell_amt = await upsell_svc.calc_upsell_amount(db, item.upsell_options)
            if "real_scale" in codes and not item.scale_calibration:
                errors.append({"task_uuid": item.task_uuid, "error": "scale_calibration required"})
                continue
            amount = base + upsell_amt
            order = Order(
                user_id=actor.id,
                company_id=company.id,
                task_uuid=item.task_uuid,
                category=item.category,
                tier=item.tier,
                status="pending",
                amount=amount,
                amount_original=base,
                discount_amount=0,
                upsell_options=codes,
                upsell_amount=upsell_amt,
                scale_calibration=item.scale_calibration,
            )
            db.add(order)
            await db.flush()
            if actor.balance >= amount or company.balance >= amount:
                if company.balance >= amount:
                    from app.services import company_balance as company_bal

                    await company_bal.charge_company(
                        db,
                        company=company,
                        amount=amount,
                        user=actor,
                        description=f"Bulk заказ #{order.id}",
                        order_id=order.id,
                    )
                else:
                    actor.balance -= amount
                order.status = "queued"
                prefix = item.photos_prefix or photos_service.photos_prefix(item.task_uuid)
                await queue_service.enqueue(
                    db,
                    task_id=item.task_uuid,
                    order_id=order.id,
                    company_id=company.id,
                    payload={
                        "category": order.category,
                        "tier": order.tier,
                        "user_id": actor.id,
                        "order_id": order.id,
                        "company_id": company.id,
                        "photos_bucket": settings.MINIO_BUCKET_PHOTOS,
                        "photos_prefix": prefix,
                        "models_bucket": settings.MINIO_BUCKET_MODELS,
                        "upsell_options": codes,
                        "scale_calibration": item.scale_calibration,
                    },
                    priority="high" if item.tier == "large" else "normal",
                )
            else:
                order.status = "awaiting_payment"
            try:
                from app.services import company_webhooks as wh

                await wh.emit(
                    db,
                    company_id=company.id,
                    event="order.created",
                    payload={
                        "order_id": order.id,
                        "task_uuid": order.task_uuid,
                        "status": order.status,
                        "amount": order.amount,
                        "tier": order.tier,
                        "category": order.category,
                    },
                )
            except Exception:  # noqa: BLE001
                pass
            created.append(
                {
                    "task_uuid": item.task_uuid,
                    "id": order.id,
                    "status": order.status,
                    "amount": order.amount,
                }
            )
        except HTTPException as exc:
            errors.append({"task_uuid": item.task_uuid, "error": str(exc.detail)})
        except Exception as exc:  # noqa: BLE001
            errors.append({"task_uuid": item.task_uuid, "error": str(exc)[:200]})
    await db.commit()
    return {"created": created, "errors": errors, "company_id": company.id}
