"""Удаление компании: grace 30 дней §9.8."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Company, CompanyMember

GRACE_DAYS = 30


def _settings(company: Company) -> dict:
    return dict(company.settings or {})


def deletion_state(company: Company) -> dict[str, Any]:
    st = _settings(company)
    req = st.get("deletion_requested_at")
    sched = st.get("deletion_scheduled_at")
    return {
        "pending_deletion": company.status == "pending_deletion",
        "deletion_requested_at": req,
        "deletion_scheduled_at": sched,
        "grace_days": GRACE_DAYS,
    }


async def request_deletion(db: AsyncSession, company: Company, *, user_id: int) -> dict[str, Any]:
    if company.owner_id != user_id:
        raise HTTPException(403, "Только Owner может запросить удаление компании")
    if company.status == "pending_deletion":
        return deletion_state(company)
    now = datetime.now(timezone.utc)
    scheduled = now + timedelta(days=GRACE_DAYS)
    st = _settings(company)
    st["deletion_requested_at"] = now.isoformat()
    st["deletion_scheduled_at"] = scheduled.isoformat()
    st["deletion_requested_by"] = user_id
    company.settings = st
    company.status = "pending_deletion"
    await db.flush()
    return {
        **deletion_state(company),
        "message": f"Компания будет удалена через {GRACE_DAYS} дней, если не отменить",
    }


async def cancel_deletion(db: AsyncSession, company: Company, *, user_id: int) -> dict[str, Any]:
    if company.owner_id != user_id:
        raise HTTPException(403, "Только Owner может отменить удаление")
    if company.status != "pending_deletion":
        return {"ok": True, "cancelled": False, **deletion_state(company)}
    st = _settings(company)
    st.pop("deletion_requested_at", None)
    st.pop("deletion_scheduled_at", None)
    st.pop("deletion_requested_by", None)
    company.settings = st
    company.status = "active"
    await db.flush()
    return {"ok": True, "cancelled": True, **deletion_state(company)}


async def process_due_deletions(db: AsyncSession, *, limit: int = 20) -> dict[str, Any]:
    """Celery: физическое удаление после grace period."""
    from app.services.minio import minio_service

    now = datetime.now(timezone.utc)
    rows = (
        await db.scalars(
            select(Company).where(Company.status == "pending_deletion").order_by(Company.id).limit(limit)
        )
    ).all()
    purged: list[int] = []
    skipped: list[int] = []
    for company in rows:
        st = _settings(company)
        raw = st.get("deletion_scheduled_at")
        if not raw:
            skipped.append(company.id)
            continue
        try:
            sched = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            skipped.append(company.id)
            continue
        if sched > now:
            skipped.append(company.id)
            continue
        prefix = f"backups/company_{company.id}/"
        try:
            minio_service.delete_prefix(settings.MINIO_BUCKET_BACKUPS, prefix)
        except Exception:  # noqa: BLE001
            pass
        members = (
            await db.scalars(select(CompanyMember).where(CompanyMember.company_id == company.id))
        ).all()
        for m in members:
            await db.delete(m)
        company.status = "deleted"
        company.balance = 0
        st["purged_at"] = now.isoformat()
        company.settings = st
        purged.append(company.id)
    await db.commit()
    return {"purged": purged, "skipped": skipped, "as_of": now.isoformat()}
