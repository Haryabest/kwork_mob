"""Асинхронный экспорт всех данных компании §9.5.2."""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Company, CompanyDataExport, CompanyMember, Model3D, Order, User
from app.services import restore_sources as restore_svc
from app.services.email import _send_email
from app.services.marketplace_upload import _load_model_files
from app.services.minio import minio_service

logger = logging.getLogger(__name__)

EXPORT_EXPIRES_DAYS = 7


async def request_export(db: AsyncSession, *, company: Company, user: User) -> CompanyDataExport:
    pending = await db.scalar(
        select(CompanyDataExport)
        .where(
            CompanyDataExport.company_id == company.id,
            CompanyDataExport.status.in_(("pending", "processing")),
        )
        .order_by(CompanyDataExport.id.desc())
        .limit(1)
    )
    if pending:
        return pending

    row = CompanyDataExport(
        company_id=company.id,
        requested_by_user_id=user.id,
        status="pending",
        notify_email=user.email,
    )
    db.add(row)
    await db.flush()
    return row


async def get_export(db: AsyncSession, *, company_id: int, export_id: int) -> CompanyDataExport | None:
    return await db.scalar(
        select(CompanyDataExport).where(
            CompanyDataExport.id == export_id,
            CompanyDataExport.company_id == company_id,
        )
    )


async def list_exports(db: AsyncSession, *, company_id: int, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(CompanyDataExport)
            .where(CompanyDataExport.company_id == company_id)
            .order_by(CompanyDataExport.id.desc())
            .limit(min(limit, 50))
        )
    ).all()
    return [export_to_dict(r) for r in rows]


def export_to_dict(row: CompanyDataExport) -> dict[str, Any]:
    return {
        "id": row.id,
        "company_id": row.company_id,
        "status": row.status,
        "download_url": row.download_url,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


async def build_company_export_zip(db: AsyncSession, company_id: int) -> bytes:
    company = await db.get(Company, company_id)
    if not company:
        raise ValueError(f"company {company_id} not found")

    orders = (
        await db.scalars(select(Order).where(Order.company_id == company_id).order_by(Order.id))
    ).all()
    models = (
        await db.scalars(select(Model3D).where(Model3D.company_id == company_id).order_by(Model3D.id))
    ).all()
    members = (
        await db.scalars(select(CompanyMember).where(CompanyMember.company_id == company_id))
    ).all()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        meta = {
            "company_id": company.id,
            "company_name": company.name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "orders_count": len(orders),
            "models_count": len(models),
        }
        zf.writestr(
            "metadata/company.json",
            json.dumps(meta, ensure_ascii=False, indent=2),
        )
        zf.writestr(
            "metadata/orders.json",
            json.dumps(
                [
                    {
                        "id": o.id,
                        "task_uuid": o.task_uuid,
                        "status": o.status,
                        "amount": o.amount,
                        "category": o.category,
                        "tier": o.tier,
                        "created_at": o.created_at.isoformat() if o.created_at else None,
                    }
                    for o in orders
                ],
                ensure_ascii=False,
                indent=2,
            ),
        )
        zf.writestr(
            "metadata/members.json",
            json.dumps(
                [
                    {
                        "user_id": m.user_id,
                        "role": m.role,
                        "role_id": m.role_id,
                    }
                    for m in members
                ],
                ensure_ascii=False,
                indent=2,
            ),
        )

        for model in models:
            order = await db.get(Order, model.order_id) if model.order_id else None
            base = f"models/{model.uuid}/"
            model_meta = {
                "uuid": model.uuid,
                "order_id": model.order_id,
                "publish_status": model.publish_status,
                "glb_url": model.glb_url,
                "created_at": model.created_at.isoformat() if model.created_at else None,
            }
            zf.writestr(f"{base}metadata.json", json.dumps(model_meta, ensure_ascii=False, indent=2))

            if model.glb_url:
                try:
                    glb, usdz = _load_model_files(model)
                    zf.writestr(f"{base}model.glb", glb)
                    if usdz:
                        zf.writestr(f"{base}model.usdz", usdz)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("export glb %s: %s", model.uuid, exc)

            try:
                bucket, key = restore_svc._find_source_zip(model, order)
                src = minio_service.download_bytes(bucket, key)
                zf.writestr(f"sources/{model.uuid}/source.zip", src)
            except Exception:  # noqa: BLE001
                pass

    return buf.getvalue()


async def process_export(db: AsyncSession, export_id: int) -> dict[str, Any]:
    row = await db.get(CompanyDataExport, export_id)
    if not row or row.status not in ("pending", "processing"):
        return {"skipped": True, "export_id": export_id}

    row.status = "processing"
    await db.flush()

    try:
        zip_bytes = await build_company_export_zip(db, row.company_id)
        ttl_sec = max(86400, int(settings.COMPANY_DATA_EXPORT_URL_TTL_DAYS or EXPORT_EXPIRES_DAYS) * 86400)
        key = f"exports/company_{row.company_id}/export_{row.id}.zip"
        bucket = settings.MINIO_BUCKET_BACKUPS
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(zip_bytes)
            tmp_path = tmp.name
        try:
            minio_service.upload_file(bucket, key, tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        url = minio_service.generate_presigned_url(bucket, key, expires=ttl_sec, method="get_object")
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_sec)
        row.status = "completed"
        row.storage_bucket = bucket
        row.storage_key = key
        row.download_url = url
        row.expires_at = expires_at
        row.completed_at = datetime.now(timezone.utc)
        row.zip_bytes = len(zip_bytes)
        await db.flush()

        if row.notify_email:
            subject = "Экспорт данных компании готов"
            body = (
                f"Архив данных компании #{row.company_id} сформирован.\n\n"
                f"Ссылка (действует {settings.COMPANY_DATA_EXPORT_URL_TTL_DAYS} дн.):\n{url}\n"
            )
            try:
                await _send_email(row.notify_email, subject, body)
            except Exception as exc:  # noqa: BLE001
                logger.warning("export email failed export=%s: %s", export_id, exc)

        return export_to_dict(row)
    except Exception as exc:  # noqa: BLE001
        logger.exception("company export %s failed", export_id)
        row.status = "failed"
        row.error = str(exc)[:500]
        row.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return {"export_id": export_id, "status": "failed", "error": row.error}
