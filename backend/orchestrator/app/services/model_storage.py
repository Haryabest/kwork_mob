"""Продление хранения исходников §9.1.2 (лимит 3×) + корзина §3.3 / §9."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog, Model3D, User

MAX_EXTENDS = 3
TRASH_DAYS = 30


def ttl_days() -> int:
    return max(7, min(int(getattr(settings, "SOURCE_PHOTOS_TTL_DAYS", 30) or 30), 90))


def default_expires_at(created: datetime | None = None) -> datetime:
    base = created or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base + timedelta(days=ttl_days())


def ensure_expires(model: Model3D) -> datetime:
    if model.source_expires_at:
        exp = model.source_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp
    exp = default_expires_at(model.created_at)
    model.source_expires_at = exp
    return exp


def storage_meta(model: Model3D) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    exp = ensure_expires(model)
    days_left = (exp.date() - now.date()).days
    extends = int(model.source_extend_count or 0)
    return {
        "source_expires_at": exp.isoformat(),
        "days_left": days_left,
        "source_extend_count": extends,
        "extends_remaining": max(0, MAX_EXTENDS - extends),
        "max_extends": MAX_EXTENDS,
        "ttl_days": ttl_days(),
        "trashed_at": model.trashed_at.isoformat() if model.trashed_at else None,
        "in_trash": model.trashed_at is not None,
    }


async def extend_storage(db: AsyncSession, *, model: Model3D, user: User) -> dict[str, Any]:
    """Продлить хранение ещё на TTL дней, макс 3 раза (§9.1.2)."""
    if model.trashed_at:
        raise HTTPException(400, "Модель в корзине — сначала восстановите")
    extends = int(model.source_extend_count or 0)
    if extends >= MAX_EXTENDS:
        raise HTTPException(400, f"Лимит продлений исчерпан ({MAX_EXTENDS})")
    exp = ensure_expires(model)
    now = datetime.now(timezone.utc)
    base = exp if exp > now else now
    model.source_expires_at = base + timedelta(days=ttl_days())
    model.source_extend_count = extends + 1
    db.add(
        AuditLog(
            company_id=model.company_id,
            user_id=user.id,
            action="source_storage_extend",
            details={
                "model_uuid": model.uuid,
                "extend_count": model.source_extend_count,
                "expires_at": model.source_expires_at.isoformat(),
            },
        )
    )
    await db.flush()
    return {"ok": True, **storage_meta(model), "message": f"Хранение продлено на {ttl_days()} дней"}


async def trash_model(db: AsyncSession, *, model: Model3D, user: User) -> dict[str, Any]:
    """В корзину на 30 дней (§3.3.1)."""
    if model.trashed_at:
        raise HTTPException(400, "Уже в корзине")
    model.trashed_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            company_id=model.company_id,
            user_id=user.id,
            action="model_trash",
            details={"model_uuid": model.uuid},
        )
    )
    await db.flush()
    return {
        "ok": True,
        "model_uuid": model.uuid,
        "trashed_at": model.trashed_at.isoformat(),
        "purge_at": (model.trashed_at + timedelta(days=TRASH_DAYS)).isoformat(),
        "message": f"Модель в корзине на {TRASH_DAYS} дней",
    }


async def restore_from_trash(db: AsyncSession, *, model: Model3D, user: User) -> dict[str, Any]:
    if not model.trashed_at:
        raise HTTPException(400, "Модель не в корзине")
    model.trashed_at = None
    db.add(
        AuditLog(
            company_id=model.company_id,
            user_id=user.id,
            action="model_restore_from_trash",
            details={"model_uuid": model.uuid},
        )
    )
    await db.flush()
    return {"ok": True, "model_uuid": model.uuid, "message": "Восстановлено из корзины"}


async def list_trash(db: AsyncSession, user: User) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(Model3D)
            .where(Model3D.trashed_at.is_not(None), Model3D.user_id == user.id)
            .order_by(Model3D.trashed_at.desc())
            .limit(200)
        )
    ).all()
    out = []
    for m in rows:
        purge = m.trashed_at + timedelta(days=TRASH_DAYS) if m.trashed_at else None
        out.append(
            {
                "uuid": m.uuid,
                "order_id": m.order_id,
                "publish_status": m.publish_status,
                "trashed_at": m.trashed_at.isoformat() if m.trashed_at else None,
                "purge_at": purge.isoformat() if purge else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
        )
    return out


async def mass_extend_company_storage(
    db: AsyncSession,
    *,
    company_id: int,
    user: User,
    limit: int = 500,
) -> dict[str, Any]:
    """Owner: продлить хранение для всех моделей компании (§9.1.2)."""
    rows = (
        await db.scalars(
            select(Model3D)
            .where(
                Model3D.company_id == company_id,
                Model3D.trashed_at.is_(None),
                Model3D.source_extend_count < MAX_EXTENDS,
            )
            .order_by(Model3D.id.asc())
            .limit(limit)
        )
    ).all()
    extended = 0
    skipped = 0
    for model in rows:
        extends = int(model.source_extend_count or 0)
        if extends >= MAX_EXTENDS:
            skipped += 1
            continue
        exp = ensure_expires(model)
        now = datetime.now(timezone.utc)
        base = exp if exp > now else now
        model.source_expires_at = base + timedelta(days=ttl_days())
        model.source_extend_count = extends + 1
        extended += 1
    if extended:
        db.add(
            AuditLog(
                company_id=company_id,
                user_id=user.id,
                action="source_storage_mass_extend",
                details={
                    "extended": extended,
                    "skipped_at_limit": skipped,
                    "ttl_days": ttl_days(),
                },
            )
        )
    await db.flush()
    return {
        "ok": True,
        "extended": extended,
        "skipped_at_limit": skipped,
        "message": f"Продлено {extended} моделей на {ttl_days()} дней",
    }


async def purge_expired_trash(db: AsyncSession, *, limit: int = 100) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=TRASH_DAYS)
    rows = (
        await db.scalars(
            select(Model3D)
            .where(Model3D.trashed_at.is_not(None), Model3D.trashed_at <= cutoff)
            .limit(limit)
        )
    ).all()
    n = 0
    for m in rows:
        m.glb_url = None
        m.usdz_url = None
        m.publish_status = "purged"
        n += 1
    await db.commit()
    return {"purged": n}
