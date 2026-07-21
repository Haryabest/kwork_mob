"""Модерация NSFW (§10.8, §11) — reports + verify 24ч + SLA + preview + blacklist."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_db_user, require_admin
from app.core.vpn import require_vpn
from app.models import AuditLog, NsfwBlock, Order, User
from app.services import photos as photos_service
from app.services.minio import minio_service


def _vpn_guard(request: Request) -> None:
    require_vpn(request)


router = APIRouter(dependencies=[Depends(_vpn_guard), Depends(require_admin)])


class VerifyBody(BaseModel):
    legal: bool
    note: str | None = None


class ManualBlockBody(BaseModel):
    order_id: int
    reason: str = "manual"


class BlacklistAddBody(BaseModel):
    word: str = Field(min_length=2, max_length=120)
    category: str = Field(default="general", max_length=32)


def _sla_fields(created_at: datetime | None) -> dict:
    from app.services.nsfw_sla_dashboard import sla_fields

    return sla_fields(created_at)


def _photo_previews(task_uuid: str | None, *, limit: int = 12, expires: int = 900) -> list[dict]:
    if not task_uuid:
        return []
    bucket = settings.MINIO_BUCKET_PHOTOS
    out: list[dict] = []
    for i, name in enumerate(photos_service.VIEW_NAMES[:limit]):
        key = f"{photos_service.photos_prefix(task_uuid)}{name}"
        if not minio_service.object_exists(bucket, key):
            continue
        try:
            url = minio_service.generate_presigned_url(
                bucket, key, expires=expires, method="get_object"
            )
        except Exception:  # noqa: BLE001
            continue
        out.append(
            {
                "index": i,
                "filename": name,
                "label": photos_service.ANGLE_LABELS[i] if i < len(photos_service.ANGLE_LABELS) else name,
                "preview_url": url,
            }
        )
    return out


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
    with_previews: bool = True,
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
            "photo_previews": _photo_previews(order.task_uuid if order else None, limit=4)
            if with_previews
            else [],
        }
        if not b.verified:
            item.update(_sla_fields(b.created_at))
        items.append(item)
    return {"items": items}


@router.get("/sla")
async def nsfw_sla_summary(db: AsyncSession = Depends(get_db)):
    """Сводка очереди модерации + SLA dashboard §10.8."""
    from app.services import nsfw_sla_dashboard as dash

    return await dash.sla_dashboard(db)


@router.post("/escalate")
async def nsfw_escalate_now(db: AsyncSession = Depends(get_db)):
    """Просроченные >24ч → Telegram (§10.8)."""
    from app.services import nsfw_sla as sla

    return await sla.escalate_overdue(db)


@router.get("/blacklist")
async def blacklist_list(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    from app.services import blacklist as bl

    return {"items": await bl.list_words(db, active_only=active_only)}


@router.post("/blacklist")
async def blacklist_add(
    body: BlacklistAddBody,
    admin: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import blacklist as bl

    row = await bl.add_word(db, word=body.word, category=body.category, admin_id=admin.id)
    await db.commit()
    return {"id": row.id, "word": row.word, "category": row.category, "is_active": row.is_active}


@router.delete("/blacklist/{word_id}")
async def blacklist_delete(
    word_id: int,
    admin: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import blacklist as bl

    await bl.remove_word(db, word_id=word_id, admin_id=admin.id)
    await db.commit()
    return {"ok": True}


@router.get("/{block_id}/photos")
async def nsfw_block_photos(block_id: int, db: AsyncSession = Depends(get_db)):
    """Превью всех 12 фото заблокированного заказа (§11 модерация)."""
    block = await db.get(NsfwBlock, block_id)
    if not block:
        raise HTTPException(404, "Блок не найден")
    order = await db.get(Order, block.order_id)
    if not order:
        raise HTTPException(404, "Заказ не найден")
    previews = _photo_previews(order.task_uuid, limit=12, expires=1800)
    return {
        "block_id": block.id,
        "order_id": order.id,
        "task_uuid": order.task_uuid,
        "items": previews,
        "expires_in": 1800,
    }


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
