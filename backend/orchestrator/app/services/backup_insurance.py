"""Верификация страхующих копий B2B §9.9."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Model3D, Order
from app.services.minio import minio_service


async def company_backup_status(db: AsyncSession, company_id: int, *, limit: int = 500) -> dict:
    rows = (
        await db.execute(
            select(Model3D, Order)
            .join(Order, Order.id == Model3D.order_id)
            .where(Model3D.company_id == company_id, Model3D.trashed_at.is_(None))
            .order_by(Model3D.id.desc())
            .limit(limit)
        )
    ).all()
    bucket = settings.MINIO_BUCKET_BACKUPS
    found = 0
    missing = 0
    samples_missing: list[str] = []
    for model, order in rows:
        keys = [
            f"backups/company_{company_id}/{order.task_uuid}/source.zip",
            f"backups/{order.user_id}/{order.task_uuid}/source.zip",
        ]
        ok = any(minio_service.object_exists(bucket, k) for k in keys)
        if ok:
            found += 1
        else:
            missing += 1
            if len(samples_missing) < 10:
                samples_missing.append(model.uuid)
    total = found + missing
    return {
        "company_id": company_id,
        "total_models": total,
        "backups_found": found,
        "backups_missing": missing,
        "coverage_ratio": round(found / total, 4) if total else 1.0,
        "samples_missing_uuids": samples_missing,
    }
