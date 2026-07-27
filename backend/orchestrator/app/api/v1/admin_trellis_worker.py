"""Admin: настройка TRELLIS GPU-воркера (Docker apply / logs / verify)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.core.security import require_admin
from app.core.vpn import require_vpn
from app.models import AuditLog
from app.services import worker_deploy as wd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

logger = logging.getLogger(__name__)


def _vpn(request: Request) -> None:
    require_vpn(request)


router = APIRouter(
    prefix="/admin/trellis/worker-config",
    tags=["TRELLIS worker"],
    dependencies=[Depends(_vpn), Depends(require_admin)],
)


class WorkerEnvBody(BaseModel):
    WORKER_ID: str | None = None
    WORKER_TOKEN: str | None = None
    WORKER_PIPELINE_MODE: str | None = None
    TRELLIS_VERSION: str | None = None
    TRELLIS2_PIPELINE_TYPE: str | None = None
    TRELLIS2_TEXTURE_SIZE: str | None = None
    TRELLIS2_DECIMATION: str | None = None
    TRELLIS2_LOW_VRAM: str | None = None
    WORKER_TRELLIS_INPROCESS: str | None = None
    WORKER_WARMUP_TRELLIS: str | None = None
    ATTN_BACKEND: str | None = None
    PYTORCH_CUDA_ALLOC_CONF: str | None = None
    NOBG_ENGINE: str | None = None
    NOBG_VIEW00_ONLY: str | None = None
    HF_TOKEN: str | None = None
    ORCHESTRATOR_WS_URL: str | None = None
    ORCHESTRATOR_HTTP_URL: str | None = None
    REDIS_URL: str | None = None
    MINIO_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str | None = None
    MINIO_SECRET_KEY: str | None = None


class TrellisWorkerConfigBody(BaseModel):
    container_name: str | None = Field(default=None, max_length=64)
    docker_image: str | None = Field(default=None, max_length=200)
    worker_repo_path: str | None = Field(default=None, max_length=500)
    hf_cache_host_path: str | None = Field(default=None, max_length=500)
    state_volume: str | None = Field(default=None, max_length=120)
    extra_hosts: str | None = Field(default=None, max_length=200)
    env: WorkerEnvBody | None = None


@router.get("")
async def get_trellis_worker_config(_: dict = Depends(require_admin)):
    return await wd.get_config(masked=True)


@router.put("")
async def put_trellis_worker_config(
    body: TrellisWorkerConfigBody,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    payload: dict[str, Any] = body.model_dump(exclude_none=True)
    if body.env:
        payload["env"] = body.env.model_dump(exclude_none=True)
    user_id = int(admin.get("sub") or 0) or None
    result = await wd.save_config(payload, user_id=user_id)
    db.add(
        AuditLog(
            user_id=user_id,
            action="trellis_worker_config_save",
            details={"container_name": result.get("container_name")},
        )
    )
    await db.commit()
    return result


@router.post("/apply")
async def apply_trellis_worker_config(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(admin.get("sub") or 0) or None
    result = await wd.apply_config(user_id=user_id)
    db.add(
        AuditLog(
            user_id=user_id,
            action="trellis_worker_config_apply",
            details={"ok": result.get("ok"), "verify_ok": (result.get("verify") or {}).get("ok")},
        )
    )
    await db.commit()
    return result


@router.get("/verify")
async def verify_trellis_worker_config(_: dict = Depends(require_admin)):
    return await wd.verify_stored_config()


@router.get("/logs")
async def trellis_worker_logs(
    tail: int = Query(300, ge=50, le=2000),
    _: dict = Depends(require_admin),
):
    return await wd.fetch_logs_async(tail=tail)
