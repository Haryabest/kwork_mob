"""Корпоративные функции: команда, приглашения, API-ключи, съёмка по ссылке."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_db_user, get_current_db_user_optional, get_current_user
from app.models import Company, CompanyInvitation, CompanyMember, Order, ShootLink, User
from app.services import api_keys as api_keys_svc
from app.services import photos as photos_service
from app.services import tariffs as tariff_svc
from app.services import upsells as upsell_svc
from app.services.queue import queue_service

router = APIRouter()


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="photographer", pattern=r"^(manager|photographer|viewer)$")
    company_id: int | None = None
    max_concurrent_orders: int | None = Field(default=3, ge=1, le=50)
    monthly_spending_limit: int | None = Field(default=None, ge=0)
    ttl_days: int = Field(default=7, ge=1, le=30)


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


class BulkOrderItem(BaseModel):
    task_uuid: str
    category: str = "other"
    tier: str = "small"
    photos_prefix: str | None = None
    upsell_options: list[str] = Field(default_factory=list)
    scale_calibration: dict | None = None


class BulkOrdersRequest(BaseModel):
    items: list[BulkOrderItem] = Field(min_length=1, max_length=100)


@router.post("/invite")
async def invite_member(
    body: InviteRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Пригласить сотрудника (email, роль, лимиты)."""
    company_id = body.company_id
    if company_id is None:
        owned = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
        if owned:
            company_id = owned.id
        else:
            # физлицо без компании — создаём personal workspace-приглашение без company
            company_id = None

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
    )
    db.add(inv)
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

    if inv.company_id:
        existing = await db.scalar(
            select(CompanyMember).where(
                CompanyMember.company_id == inv.company_id,
                CompanyMember.user_id == user.id,
            )
        )
        if not existing:
            db.add(
                CompanyMember(
                    company_id=inv.company_id,
                    user_id=user.id,
                    role=inv.role,
                    max_concurrent_orders=inv.max_concurrent_orders,
                    monthly_spending_limit=inv.monthly_spending_limit,
                )
            )
    inv.status = "accepted"
    await db.commit()
    return {"ok": True, "role": inv.role, "company_id": inv.company_id}


@router.get("/members")
async def list_members(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    owned = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
    if not owned:
        return {"items": [], "company_id": None}
    members = (
        await db.scalars(select(CompanyMember).where(CompanyMember.company_id == owned.id))
    ).all()
    items = []
    for m in members:
        u = await db.get(User, m.user_id)
        items.append(
            {
                "user_id": m.user_id,
                "email": u.email if u else None,
                "full_name": u.full_name if u else None,
                "role": m.role,
                "max_concurrent_orders": m.max_concurrent_orders,
                "monthly_spending_limit": m.monthly_spending_limit,
            }
        )
    return {"items": items, "company_id": owned.id}


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


class RoleBody(BaseModel):
    role: str


@router.patch("/members/{user_id}/role")
async def change_role(
    user_id: int,
    body: RoleBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_members as cm

    m = await cm.change_role(db, user, user_id, body.role)
    await db.commit()
    return {"user_id": m.user_id, "role": m.role}


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


@router.get("/settings")
async def get_settings(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    return {"company_id": company.id, "settings": company.settings or {}, "balance": company.balance}


class SettingsBody(BaseModel):
    settings: dict = Field(default_factory=dict)


@router.patch("/settings")
async def update_settings(
    body: SettingsBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.company_members import audit, get_owned_company

    company = await get_owned_company(db, user)
    company.settings = {**(company.settings or {}), **body.settings}
    await audit(db, company_id=company.id, user_id=user.id, action="company.settings", details=body.settings)
    await db.commit()
    return {"company_id": company.id, "settings": company.settings}


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
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import AuditLog
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    rows = (
        await db.scalars(
            select(AuditLog).where(AuditLog.company_id == company.id).order_by(AuditLog.id.desc()).limit(200)
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "action": r.action,
                "details": r.details,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/audit/export")
async def audit_export(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    import csv
    import io

    from fastapi.responses import Response

    from app.models import AuditLog
    from app.services.company_members import get_owned_company

    company = await get_owned_company(db, user)
    rows = (
        await db.scalars(
            select(AuditLog).where(AuditLog.company_id == company.id).order_by(AuditLog.id.desc()).limit(5000)
        )
    ).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "user_id", "action", "details", "created_at"])
    for r in rows:
        w.writerow([r.id, r.user_id, r.action, r.details, r.created_at.isoformat() if r.created_at else ""])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit.csv"'},
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
    amount: int = Field(ge=1, le=10_000_000)
    note: str | None = None


@router.post("/balance/topup")
async def company_topup(
    body: TopupBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_balance as bal

    data = await bal.topup_manual(db, user, body.amount, body.note)
    await db.commit()
    return data


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

@router.post("/shoot_link")
async def create_shoot_link(
    body: ShootLinkRequest | None = None,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать одноразовую ссылку для внешнего фотографа."""
    payload = body or ShootLinkRequest()
    task_uuid = payload.task_uuid or str(uuid.uuid4())
    token = secrets.token_urlsafe(24)
    link = ShootLink(
        token=token,
        task_uuid=task_uuid,
        user_id=user.id,
        company_id=payload.company_id,
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
    )
    await db.commit()
    return {
        "id": row.id,
        "name": row.name,
        "key": plain,
        "key_prefix": row.key_prefix,
        "scopes": row.scopes,
        "rate_limit_per_min": row.rate_limit_per_min,
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
            base = await tariff_svc.get_amount(db, item.tier)
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
