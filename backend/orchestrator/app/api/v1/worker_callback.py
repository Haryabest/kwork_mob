"""HTTP fallback для событий воркера, если WS оборвался (§4.3)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import release_task_lock
from app.services.task_lifecycle import mark_completed, mark_failed, requeue_task
from app.services.worker_hub import worker_hub

router = APIRouter(prefix="/worker", tags=["Worker callback"])


class WorkerEvent(BaseModel):
    type: str
    task_id: str = Field(min_length=8)
    worker_id: str | None = None
    result_url: str | None = None
    glb_url: str | None = None
    usdz_url: str | None = None
    video_360_url: str | None = None
    watermark_hmac: str | None = None
    quality_score: float | None = None
    error: str | None = None
    checkpoint_path: str | None = None


def _verify_worker_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    if authorization[7:] != settings.WORKER_TOKEN:
        raise HTTPException(403, "Invalid worker token")


@router.post("/event")
async def worker_event(body: WorkerEvent, _: None = Depends(_verify_worker_token)):
    """Дублирует WS task_completed / task_failed для HTTP fallback."""
    task_id = body.task_id
    worker_id = body.worker_id or "unknown"

    if body.type == "task_completed":
        glb_url = str(body.result_url or body.glb_url or "")
        if not glb_url:
            raise HTTPException(400, "result_url or glb_url required")
        threshold = float(os.getenv("QUALITY_THRESHOLD", "0.7"))
        if body.quality_score is not None and body.quality_score < threshold:
            async with async_session() as db:
                await mark_failed(db, task_id, f"quality_gate_failed score={body.quality_score} < {threshold}")
            await release_task_lock(task_id)
            await worker_hub.set_idle(worker_id)
            return {"ok": True, "status": "rejected", "reason": "quality"}

        async with async_session() as db:
            from sqlalchemy import select

            from app.models import TaskConflict, TaskQueue

            existing = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
            if existing and existing.status == "done":
                db.add(
                    TaskConflict(
                        task_id=task_id,
                        worker_id=worker_id,
                        reason="duplicate_completion",
                        details={"glb_url": glb_url, "via": "http"},
                    )
                )
                await db.commit()
            else:
                await mark_completed(
                    db,
                    task_id=task_id,
                    glb_url=glb_url,
                    usdz_url=body.usdz_url,
                    watermark_hmac=body.watermark_hmac,
                )
        await release_task_lock(task_id)
        await worker_hub.set_idle(worker_id)
        return {"ok": True, "status": "completed", "task_id": task_id}

    if body.type == "task_failed":
        error = str(body.error or "unknown")
        await release_task_lock(task_id)
        if "quality_gate_failed" in error:
            async with async_session() as db:
                await mark_failed(db, task_id, error)
        elif "failed_segmentation" in error or body.checkpoint_path:
            if body.checkpoint_path:
                async with async_session() as db:
                    from sqlalchemy import select

                    from app.models import TaskQueue

                    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
                    if row:
                        payload = dict(row.payload_json or {})
                        payload["checkpoint_path"] = body.checkpoint_path
                        row.payload_json = payload
                        await db.commit()
            await requeue_task(task_id)
        else:
            async with async_session() as db:
                await mark_failed(db, task_id, error)
        await worker_hub.set_idle(worker_id)
        return {"ok": True, "status": "failed", "task_id": task_id}

    raise HTTPException(400, f"Unsupported event type: {body.type}")
