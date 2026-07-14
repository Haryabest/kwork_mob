"""Аудит доступа к моделям §10.7.2 — таблица access_log.

События: download, preview, presign_get, presign_put (выдача URL).
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccessLog, Model3D, User


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def log_access(
    db: AsyncSession,
    *,
    user_id: int,
    model_uuid: str,
    action: str,
    request: Request | None = None,
    company_id: int | None = None,
    file_format: str | None = None,
) -> None:
    """Универсальная запись access_log (§10.7.2 / §10.7.7)."""
    db.add(
        AccessLog(
            user_id=user_id,
            company_id=company_id,
            model_uuid=model_uuid[:36],
            action=(action or "download")[:32],
            file_format=(file_format or None) and str(file_format)[:10],
            ip_address=_client_ip(request),
        )
    )


async def log_model_access(
    db: AsyncSession,
    *,
    model: Model3D,
    user: User,
    request: Request | None,
    action: str = "download",
    file_format: str | None = None,
) -> None:
    """Запись события скачивания / выдачи presigned URL по модели."""
    await log_access(
        db,
        user_id=user.id,
        company_id=model.company_id,
        model_uuid=model.uuid,
        action=action,
        request=request,
        file_format=file_format,
    )


def _base_query(
    *,
    company_id: int | None = None,
    user_id: int | None = None,
    model_uuid: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    q = select(AccessLog).order_by(AccessLog.id.desc())
    if company_id is not None:
        q = q.where(AccessLog.company_id == company_id)
    if user_id is not None:
        q = q.where(AccessLog.user_id == user_id)
    if model_uuid:
        q = q.where(AccessLog.model_uuid == model_uuid)
    if date_from is not None:
        q = q.where(AccessLog.created_at >= date_from)
    if date_to is not None:
        q = q.where(AccessLog.created_at <= date_to)
    return q


def row_public(r: AccessLog) -> dict[str, Any]:
    return {
        "id": r.id,
        "user_id": r.user_id,
        "company_id": r.company_id,
        "model_uuid": r.model_uuid,
        "action": r.action,
        "file_format": r.file_format,
        "ip_address": r.ip_address,
        "timestamp": r.created_at.isoformat() if r.created_at else None,
    }


async def list_access_logs(
    db: AsyncSession,
    *,
    company_id: int | None = None,
    user_id: int | None = None,
    model_uuid: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]:
    q = _base_query(
        company_id=company_id,
        user_id=user_id,
        model_uuid=model_uuid,
        date_from=date_from,
        date_to=date_to,
    )
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (await db.scalars(q.offset(offset).limit(min(limit, 1000)))).all()
    return {
        "total": int(total or 0),
        "items": [row_public(r) for r in rows],
    }


def to_csv(items: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "timestamp", "user_id", "company_id", "model_uuid", "action", "file_format", "ip_address"])
    for r in items:
        w.writerow(
            [
                r.get("id"),
                r.get("timestamp"),
                r.get("user_id"),
                r.get("company_id"),
                r.get("model_uuid"),
                r.get("action"),
                r.get("file_format"),
                r.get("ip_address"),
            ]
        )
    return buf.getvalue().encode("utf-8-sig")
