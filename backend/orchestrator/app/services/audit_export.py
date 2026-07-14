"""Ежемесячный экспорт audit/access логов в MinIO audit-logs (§10.7.7)."""

from __future__ import annotations

import gzip
import io
import logging
from calendar import monthrange
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccessLog, AuditLog
from app.services.minio import minio_service

logger = logging.getLogger(__name__)

BUCKET = "audit-logs"


def _month_window(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last = monthrange(year, month)[1]
    end = datetime(year, month, last, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _prev_month(now: datetime | None = None) -> tuple[int, int]:
    now = now or datetime.now(timezone.utc)
    if now.month == 1:
        return now.year - 1, 12
    return now.year, now.month - 1


def _csv_gz(header: list[str], rows: list[list[Any]]) -> bytes:
    import csv

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return gzip.compress(buf.getvalue().encode("utf-8-sig"))


async def export_month(
    db: AsyncSession,
    *,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    """Экспорт audit_log + access_log за календарный месяц → s3://audit-logs/YYYY-MM/."""
    if year is None or month is None:
        year, month = _prev_month()
    start, end = _month_window(year, month)
    prefix = f"{year:04d}-{month:02d}"

    minio_service.ensure_buckets()

    audit_rows = (
        await db.scalars(
            select(AuditLog)
            .where(AuditLog.created_at >= start, AuditLog.created_at <= end)
            .order_by(AuditLog.id)
        )
    ).all()
    access_rows = (
        await db.scalars(
            select(AccessLog)
            .where(AccessLog.created_at >= start, AccessLog.created_at <= end)
            .order_by(AccessLog.id)
        )
    ).all()

    audit_csv = _csv_gz(
        ["id", "company_id", "user_id", "action", "details", "created_at"],
        [
            [
                r.id,
                r.company_id,
                r.user_id,
                r.action,
                str(r.details or ""),
                r.created_at.isoformat() if r.created_at else "",
            ]
            for r in audit_rows
        ],
    )
    access_csv = _csv_gz(
        ["id", "user_id", "company_id", "model_uuid", "action", "file_format", "ip_address", "created_at"],
        [
            [
                r.id,
                r.user_id,
                r.company_id,
                r.model_uuid,
                r.action,
                r.file_format or "",
                r.ip_address or "",
                r.created_at.isoformat() if r.created_at else "",
            ]
            for r in access_rows
        ],
    )

    audit_key = f"{prefix}/audit_log.csv.gz"
    access_key = f"{prefix}/access_log.csv.gz"
    meta = {
        "period": prefix,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "audit_rows": len(audit_rows),
        "access_rows": len(access_rows),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    import json

    meta_bytes = json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8")

    minio_service.upload_bytes(BUCKET, audit_key, audit_csv, content_type="application/gzip")
    minio_service.upload_bytes(BUCKET, access_key, access_csv, content_type="application/gzip")
    minio_service.upload_bytes(
        BUCKET,
        f"{prefix}/manifest.json",
        meta_bytes,
        content_type="application/json",
    )

    logger.info(
        "audit export %s: audit=%s access=%s → s3://%s/%s/",
        prefix,
        len(audit_rows),
        len(access_rows),
        BUCKET,
        prefix,
    )
    return {
        "ok": True,
        "bucket": BUCKET,
        "prefix": prefix,
        "keys": [audit_key, access_key, f"{prefix}/manifest.json"],
        **meta,
    }
