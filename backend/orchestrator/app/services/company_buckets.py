"""Dedicated MinIO buckets для крупных B2B §9.5.1."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Company
from app.services.minio import minio_service

logger = logging.getLogger(__name__)


def dedicated_bucket_name(company_id: int) -> str:
    return f"company_{company_id}_models"


def resolve_models_bucket(company: Company | None) -> str:
    if not company:
        return settings.MINIO_BUCKET_MODELS
    cfg = dict(company.settings or {})
    bucket = (cfg.get("dedicated_bucket") or "").strip()
    return bucket or settings.MINIO_BUCKET_MODELS


async def models_bucket_for_company(db: AsyncSession, company_id: int | None) -> str:
    if not company_id:
        return settings.MINIO_BUCKET_MODELS
    company = await db.get(Company, company_id)
    return resolve_models_bucket(company)


def provision_dedicated_bucket(company_id: int) -> dict[str, Any]:
    """Создать bucket + SSE, настроить replication hook."""
    name = dedicated_bucket_name(company_id)
    minio_service.ensure_bucket(name)
    from app.services import minio_replication as repl

    repl_status = repl.replication_status_for_bucket(name)
    return {
        "bucket": name,
        "created": True,
        "replication": repl_status,
    }


async def enable_dedicated_bucket(db: AsyncSession, company: Company) -> dict[str, Any]:
    info = provision_dedicated_bucket(company.id)
    cfg = dict(company.settings or {})
    cfg["dedicated_bucket"] = info["bucket"]
    cfg["dedicated_bucket_enabled_at"] = datetime.now(timezone.utc).isoformat()
    company.settings = cfg
    await db.flush()
    logger.info("Dedicated bucket enabled company=%s bucket=%s", company.id, info["bucket"])
    return info


async def disable_dedicated_bucket(db: AsyncSession, company: Company) -> dict[str, Any]:
    cfg = dict(company.settings or {})
    old = cfg.pop("dedicated_bucket", None)
    cfg.pop("dedicated_bucket_enabled_at", None)
    company.settings = cfg
    await db.flush()
    return {"disabled": True, "previous_bucket": old}
