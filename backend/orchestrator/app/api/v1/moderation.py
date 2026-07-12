"""Модерация NSFW (§10.8, §11) — reports + verify 24ч."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user, require_admin
from app.core.vpn import require_vpn
from app.models import AuditLog, NsfwBlock, Order, User


def _vpn_guard(request: Request) -> None:
    require_vpn(request)


router = APIRouter(dependencies=[Depends(_vpn_guard), Depends(require_admin)])


class VerifyBody(BaseModel):
    legal: bool
    note: str | None = None


class ManualBlockBody(BaseModel):
    order_id: int
    reason: str = "manual"


def _sla_fields(created_at: datetime | None) -> dict:
    now = datetime.now(timezone.utc)
    created = created_at or now
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    deadline = created + timedelta(hours=24)
    left = (deadline - now).total_seconds()
    return {
        "deadline_at": deadline.isoformat(),
        "hours_left": round(left / 3600, 2),
        "overdue": left < 0,
    }


@router.post("/block")
async def manual_block(
    body: ManualBlockBody,
    admin: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, body.order_id)
    if not order:
        raise HTTPException(404, "Заказ не найден")
    user = await db.get(User, order.user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    order.status = "blocked_nsfw"
    if user.status != "blocked_permanent":
        user.status = "blocked_pending_review"
    block = NsfwBlock(
        order_id=order.id,
        user_id=user.id,
        reason=(body.reason or "manual")[:50],
        refunded=False,
        verified=False,
    )
    db.add(block)
    db.add(
        AuditLog(
            company_id=order.company_id,
            user_id=admin.id,
            action="nsfw_manual_block",
            details={"order_id": order.id, "target_user_id": user.id},
        )
    )
    await db.commit()
    await db.refresh(block)
    return {"id": block.id, "order_id": order.id, "user_id": user.id}


@router.get("/reports")
async def nsfw_reports(
    verified: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(NsfwBlock).order_by(NsfwBlock.id.desc()).limit(200)
    if verified is not None:
        q = q.where(NsfwBlock.verified.is_(verified))
    rows = (await db.scalars(q)).all()
    items = []
    for b in rows:
        order = await db.get(Order, b.order_id)
        u = await db.get(User, b.user_id)
        item = {
            "id": b.id,
            "order_id": b.order_id,
            "user_id": b.user_id,
            "user_email": u.email if u else None,
            "user_status": u.status if u else None,
            "reason": b.reason,
            "refunded": b.refunded,
            "verified": b.verified,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "order_status": order.status if order else None,
            "task_uuid": order.task_uuid if order else None,
            "amount": order.amount if order else None,
        }
        if not b.verified:
            item.update(_sla_fields(b.created_at))
        items.append(item)
    return {"items": items}


@router.post("/{block_id}/verify")
async def verify_nsfw(
    block_id: int,
    body: VerifyBody,
    admin: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """legal=true → ложное срабатывание (разблок); legal=false → permanent ban."""
    block = await db.get(NsfwBlock, block_id)
    if not block:
        raise HTTPException(404, "Блок не найден")
    if block.verified:
        raise HTTPException(400, "Уже проверено")
    user = await db.get(User, block.user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    block.verified = True
    if body.legal:
        if user.status == "blocked_pending_review":
            user.status = "active"
        action = "nsfw_false_positive"
        # средства уже возвращены при авто-блоке; при manual без refund — баланс/карта
        if not block.refunded:
            order = await db.get(Order, block.order_id)
            if order:
                from app.services.refunds import refund_order

                meta = await refund_order(
                    db, order, reason="NSFW false positive", user=user, prefer_card=True
                )
                block.refunded = bool(meta.get("refunded"))
    else:
        user.status = "blocked_permanent"
        action = "nsfw_confirmed_violation"

    db.add(
        AuditLog(
            user_id=admin.id,
            action=action,
            details={
                "block_id": block.id,
                "order_id": block.order_id,
                "target_user_id": user.id,
                "note": body.note,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "refunded": block.refunded,
            },
        )
    )
    await db.commit()
    return {
        "id": block.id,
        "verified": True,
        "user_status": user.status,
        "action": action,
        "refunded": block.refunded,
    }
