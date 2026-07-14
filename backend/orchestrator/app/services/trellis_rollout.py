"""TRELLIS rolling update / rollback §18."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Company, WorkerNode

logger = logging.getLogger(__name__)

REDIS_KEY = "trellis:rollout"
DEFAULT_ALLOWED = ["1", "2", "trellis-1", "trellis-2", "v1", "v2"]


def normalize_version(raw: str | None) -> str:
    v = (raw or "").strip().lower()
    if not v:
        return ""
    if v in ("1", "v1", "trellis-1", "trellis1"):
        return "1"
    if v in ("2", "v2", "trellis-2", "trellis2", "trellis.2"):
        return "2"
    return v


async def _redis_get() -> dict[str, Any]:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        raw = await redis.get(REDIS_KEY)
        if not raw:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode()
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("trellis rollout redis: %s", exc)
        return {}


async def _redis_set(data: dict[str, Any]) -> None:
    from app.core.redis import get_redis

    redis = await get_redis()
    await redis.set(REDIS_KEY, json.dumps(data, ensure_ascii=False))


async def get_rollout_config(db: AsyncSession) -> dict[str, Any]:
    stored = await _redis_get()
    rows = (await db.scalars(select(WorkerNode))).all()
    versions: dict[str, int] = {}
    maintenance = 0
    for w in rows:
        meta = w.meta or {}
        if meta.get("maintenance"):
            maintenance += 1
        ver = normalize_version(str(meta.get("trellis_version") or meta.get("version") or ""))
        if ver:
            versions[ver] = versions.get(ver, 0) + 1
    mixed = len(versions) > 1
    return {
        "target_version": stored.get("target_version") or "2",
        "default_docker_image": stored.get("default_docker_image") or "",
        "allowed_versions": stored.get("allowed_versions") or DEFAULT_ALLOWED,
        "workers_by_version": versions,
        "mixed_versions": mixed,
        "maintenance_count": maintenance,
        "alert_mixed": mixed,
    }


async def put_rollout_config(
    db: AsyncSession,
    *,
    target_version: str,
    default_docker_image: str | None,
    allowed_versions: list[str] | None,
    user_id: int | None = None,
) -> dict[str, Any]:
    tv = normalize_version(target_version) or "2"
    allowed = [normalize_version(v) or v for v in (allowed_versions or DEFAULT_ALLOWED)]
    if tv not in allowed and tv:
        allowed.append(tv)
    payload = {
        "target_version": tv,
        "default_docker_image": (default_docker_image or "").strip(),
        "allowed_versions": allowed,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await _redis_set(payload)
    db.add(
        AuditLog(
            user_id=user_id,
            action="trellis_rollout_config",
            details=payload,
        )
    )
    await db.flush()
    return await get_rollout_config(db)


async def is_version_allowed(version: str) -> bool:
    cfg = await _redis_get()
    allowed = cfg.get("allowed_versions") or DEFAULT_ALLOWED
    v = normalize_version(version)
    if not v:
        return True
    norm_allowed = {normalize_version(a) or a for a in allowed}
    return v in norm_allowed or version in allowed


async def set_worker_maintenance(
    db: AsyncSession,
    worker_id: str,
    *,
    enabled: bool,
    user_id: int | None = None,
) -> dict[str, Any]:
    node = await db.get(WorkerNode, worker_id)
    if not node:
        raise HTTPException(404, "Воркер не найден")
    meta = dict(node.meta or {})
    meta["maintenance"] = bool(enabled)
    node.meta = meta
    db.add(
        AuditLog(
            user_id=user_id,
            action="worker_maintenance_on" if enabled else "worker_maintenance_off",
            details={"worker_id": worker_id},
        )
    )
    await db.flush()
    try:
        from app.services.worker_hub import worker_hub

        conn = await worker_hub.get(worker_id)
        if conn:
            await worker_hub.touch(worker_id, meta={"maintenance": bool(enabled)})
    except Exception:  # noqa: BLE001
        pass
    return {"worker_id": worker_id, "maintenance": enabled}


async def rollback_worker(
    db: AsyncSession,
    worker_id: str,
    *,
    trellis_version: str,
    docker_image: str | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """§18.4.1: pin worker на предыдущую версию (meta для ops runbook)."""
    node = await db.get(WorkerNode, worker_id)
    if not node:
        raise HTTPException(404, "Воркер не найден")
    new_v = normalize_version(trellis_version) or trellis_version
    old_meta = dict(node.meta or {})
    old_v = old_meta.get("trellis_version")
    meta = {**old_meta, "trellis_version": new_v, "maintenance": True, "pinned_version": new_v}
    if docker_image:
        meta["docker_image"] = docker_image
    node.meta = meta
    db.add(
        AuditLog(
            user_id=user_id,
            action="trellis_worker_rollback",
            details={
                "worker_id": worker_id,
                "old_version": old_v,
                "new_version": new_v,
                "docker_image": docker_image,
            },
        )
    )
    await db.flush()
    return {
        "worker_id": worker_id,
        "trellis_version": new_v,
        "docker_image": docker_image,
        "maintenance": True,
        "message": "Откат зафиксирован. Перезапустите контейнер с указанным образом и снимите maintenance.",
    }


async def rollout_worker(
    db: AsyncSession,
    worker_id: str,
    *,
    trellis_version: str,
    docker_image: str | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """§18.3.2: maintenance + target version для rolling update."""
    cfg = await get_rollout_config(db)
    new_v = normalize_version(trellis_version) or normalize_version(str(cfg.get("target_version") or "2"))
    node = await db.get(WorkerNode, worker_id)
    if not node:
        raise HTTPException(404, "Воркер не найден")
    old_meta = dict(node.meta or {})
    meta = {
        **old_meta,
        "trellis_version": new_v,
        "maintenance": True,
        "rollout_pending": True,
    }
    if docker_image:
        meta["docker_image"] = docker_image
    elif cfg.get("default_docker_image"):
        meta["docker_image"] = cfg["default_docker_image"]
    node.meta = meta
    db.add(
        AuditLog(
            user_id=user_id,
            action="trellis_worker_rollout",
            details={
                "worker_id": worker_id,
                "old_version": old_meta.get("trellis_version"),
                "new_version": new_v,
                "docker_image": meta.get("docker_image"),
            },
        )
    )
    await db.flush()
    return {
        "worker_id": worker_id,
        "trellis_version": new_v,
        "docker_image": meta.get("docker_image"),
        "maintenance": True,
        "message": "Rollout: maintenance ON. Обновите образ и перезапустите воркер.",
    }


async def clear_worker_maintenance(
    db: AsyncSession,
    worker_id: str,
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    node = await db.get(WorkerNode, worker_id)
    if not node:
        raise HTTPException(404, "Воркер не найден")
    meta = dict(node.meta or {})
    meta["maintenance"] = False
    meta.pop("rollout_pending", None)
    node.meta = meta
    db.add(
        AuditLog(
            user_id=user_id,
            action="trellis_worker_rollout_complete",
            details={"worker_id": worker_id, "trellis_version": meta.get("trellis_version")},
        )
    )
    await db.flush()
    return {"worker_id": worker_id, "maintenance": False}


async def list_history(db: AsyncSession, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(AuditLog)
            .where(AuditLog.action.like("trellis_%"))
            .order_by(AuditLog.id.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "details": r.details,
            "user_id": r.user_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def company_force_version(company: Company | None) -> str | None:
    if not company or not company.settings:
        return None
    raw = (company.settings or {}).get("force_trellis_version")
    if not raw or str(raw).lower() in ("default", "", "none"):
        return None
    return normalize_version(str(raw)) or str(raw)


async def resolve_required_version(db: AsyncSession, company_id: int | None) -> str | None:
    if not company_id:
        return None
    company = await db.get(Company, company_id)
    return company_force_version(company)
