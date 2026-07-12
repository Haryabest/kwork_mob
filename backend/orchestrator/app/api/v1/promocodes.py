"""Промокоды: validate (user) + admin CRUD (§8.5)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user, require_admin
from app.core.vpn import require_vpn
from app.models import Promocode, PromocodeUsage, User
from app.schemas.promocodes import PromocodeValidateRequest
from app.services import promocodes as promo_svc
from app.services import tariffs as tariff_svc

router = APIRouter()


class PromoCreateBody(BaseModel):
    name: str | None = None
    discount_type: str = Field(pattern="^(percent|fixed)$")
    discount_value: int = Field(ge=1)
    max_uses: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None
    tier: str | None = Field(default=None, pattern="^(small|large)$")
    user_id: int | None = None
    company_id: int | None = None
    code: str | None = Field(default=None, min_length=6, max_length=32)


def _vpn_admin(request: Request) -> None:
    require_vpn(request)


admin_router = APIRouter(
    prefix="/admin/promocodes",
    tags=["Промокоды admin"],
    dependencies=[Depends(_vpn_admin), Depends(require_admin)],
)


@router.post("/validate")
async def validate_promocode(
    body: PromocodeValidateRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    tier = body.tier or "small"
    if body.order_id:
        from app.models import Order

        order = await db.get(Order, body.order_id)
        if order and order.user_id == user.id:
            tier = order.tier
    info = await promo_svc.validate_for_user(
        db, plain=body.code, user=user, tier=tier, company_id=None
    )
    base = await tariff_svc.get_amount(db, tier)
    discount = promo_svc.calc_discount(base, info["discount_type"], info["discount_value"])
    return {**info, "preview_tier": tier, "base_amount": base, "discount_amount": discount, "final_amount": base - discount}


@router.get("")
async def list_my_promocodes(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Персональные + публичные активные (без полного кода)."""
    from datetime import timezone

    now = datetime.now(timezone.utc)
    rows = (
        await db.scalars(
            select(Promocode).where(
                Promocode.is_active.is_(True),
                (Promocode.user_id.is_(None)) | (Promocode.user_id == user.id),
            )
        )
    ).all()
    items = []
    for p in rows:
        if p.expires_at and p.expires_at < now:
            continue
        if p.max_uses is not None and p.used_count >= p.max_uses:
            continue
        items.append(
            {
                "id": p.id,
                "code_prefix": p.code_prefix,
                "name": p.name,
                "discount_type": p.discount_type,
                "discount_value": p.discount_value,
                "tier": p.tier,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
        )
    return {"items": items}


@admin_router.get("")
async def admin_list(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Promocode).order_by(Promocode.id.desc()).limit(200))).all()
    items = []
    for p in rows:
        total_disc = await db.scalar(
            select(func.coalesce(func.sum(PromocodeUsage.discount_amount), 0)).where(
                PromocodeUsage.promocode_id == p.id
            )
        )
        items.append(
            {
                "id": p.id,
                "code_prefix": p.code_prefix,
                "name": p.name,
                "discount_type": p.discount_type,
                "discount_value": p.discount_value,
                "max_uses": p.max_uses,
                "used_count": p.used_count,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
                "is_active": p.is_active,
                "tier": p.tier,
                "user_id": p.user_id,
                "company_id": p.company_id,
                "total_discount": int(total_disc or 0),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
        )
    return {"items": items}


@admin_router.post("")
async def admin_create(
    body: PromoCreateBody,
    admin: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    _ = admin
    plain = (body.code or promo_svc.generate_plain_code()).strip().upper()
    if len(plain) < 6:
        raise HTTPException(400, "Код слишком короткий")
    row = Promocode(
        code_hash=promo_svc.hash_code(plain),
        code_prefix=plain[:4],
        name=body.name,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        max_uses=body.max_uses,
        expires_at=body.expires_at,
        is_active=True,
        tier=body.tier,
        user_id=body.user_id,
        company_id=body.company_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "id": row.id,
        "code": plain,  # один раз
        "code_prefix": row.code_prefix,
        "name": row.name,
        "discount_type": row.discount_type,
        "discount_value": row.discount_value,
    }


@admin_router.post("/{promo_id}/deactivate")
async def admin_deactivate(promo_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(Promocode, promo_id)
    if not row:
        raise HTTPException(404, "Не найден")
    row.is_active = False
    await db.commit()
    return {"id": row.id, "is_active": False}


@admin_router.get("/{promo_id}/usages")
async def admin_usages(promo_id: int, db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(PromocodeUsage)
            .where(PromocodeUsage.promocode_id == promo_id)
            .order_by(PromocodeUsage.id.desc())
            .limit(200)
        )
    ).all()
    return {
        "items": [
            {
                "id": u.id,
                "user_id": u.user_id,
                "company_id": u.company_id,
                "order_id": u.order_id,
                "discount_amount": u.discount_amount,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in rows
        ]
    }
