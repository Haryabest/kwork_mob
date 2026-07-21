"""HTTP fallback для событий воркера, если WS оборвался (§4.3)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import release_task_lock
from app.services.task_lifecycle import handle_quality_gate_failure, mark_completed, mark_failed, requeue_task
from app.services.worker_hub import worker_hub

router = APIRouter(prefix="/worker", tags=["Worker callback"])


class WorkerEvent(BaseModel):
    model_config = {"extra": "allow"}

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
    device_model: str | None = None
    os_version: str | None = None
    segmentation: dict | None = None
    warning_size_exceeded: bool | None = None


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

    if body.type == "already_processed":
        task_id = body.task_id
        result_url = str(body.result_url or body.glb_url or "")
        cached = None
        async with async_session() as db:
            from app.services import task_idempotency as tidem

            cached = await tidem.completed_result(db, task_id)
            if not cached and result_url:
                await mark_completed(db, task_id=task_id, glb_url=result_url)
            elif cached:
                await tidem.skip_if_completed(db, task_id)
            await db.commit()
        await release_task_lock(task_id)
        await worker_hub.set_idle(worker_id)
        return {
            "ok": True,
            "status": "already_processed",
            "task_id": task_id,
            "result_url": (cached or {}).get("result_url") if cached else result_url,
        }

    if body.type == "task_completed":
        glb_url = str(body.result_url or body.glb_url or "")
        if not glb_url:
            raise HTTPException(400, "result_url or glb_url required")
        threshold = float(os.getenv("QUALITY_THRESHOLD", "0.7"))
        if body.quality_score is not None and body.quality_score < threshold:
            async with async_session() as db:
                result = await handle_quality_gate_failure(
                    db,
                    task_id,
                    f"quality_gate_failed score={body.quality_score} < {threshold}",
                )
            await release_task_lock(task_id)
            await worker_hub.set_idle(worker_id)
            return {"ok": True, "status": "rejected", "reason": "quality", **result}

        async with async_session() as db:
            from sqlalchemy import select

            from app.models import TaskQueue

            existing = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
            if existing and existing.status == "done":
                from app.services import redlock_alerts as rl

                await rl.notify_redlock_conflict(
                    task_id=task_id,
                    worker_id=worker_id,
                    reason="duplicate_completion",
                    details={"glb_url": glb_url, "via": "http"},
                )
            else:
                await mark_completed(
                    db,
                    task_id=task_id,
                    glb_url=glb_url,
                    usdz_url=body.usdz_url,
                    watermark_hmac=body.watermark_hmac,
                )
                from app.services import quality_alerts as qa

                await qa.ingest_from_worker_event(
                    db,
                    task_id=task_id,
                    data=body.model_dump(),
                    failed=False,
                )
                if body.warning_size_exceeded and existing and existing.order_id:
                    from app.models import Order
                    from app.services.task_lifecycle import _notify_order_user_push

                    order = await db.get(Order, existing.order_id)
                    if order:
                        await _notify_order_user_push(
                            db,
                            order,
                            pref_key="generation_done",
                            event_type="size_warning",
                            title="Файл оптимизирован до предела",
                            body=(
                                "Возможны трудности с загрузкой на маркетплейс. "
                                "Рекомендуем переснять с более однородным фоном."
                            ),
                        )
        await release_task_lock(task_id)
        await worker_hub.set_idle(worker_id)
        from app.services.log_writer import emit_log

        async with async_session() as db:
            await emit_log(
                db,
                source="worker",
                level="info",
                message="task_completed (http)",
                worker_id=worker_id,
                task_id=task_id,
                details={"glb_url": glb_url, "via": "http"},
            )
            await db.commit()
        return {"ok": True, "status": "completed", "task_id": task_id}

    if body.type == "segmentation_stats":
        from app.services import quality_alerts as qa

        async with async_session() as db:
            await qa.ingest_from_worker_event(db, task_id=task_id, data=body.model_dump())
            await db.commit()
        return {"ok": True, "status": "segmentation_recorded", "task_id": task_id}

    if body.type == "task_failed":
        error = str(body.error or "unknown")
        await release_task_lock(task_id)
        if "quality_gate_failed" in error:
            async with async_session() as db:
                await handle_quality_gate_failure(db, task_id, error)
        elif "failed_segmentation" in error or body.checkpoint_path:
            async with async_session() as db:
                from app.services import quality_alerts as qa

                await qa.ingest_from_worker_event(
                    db, task_id=task_id, data=body.model_dump(), failed=True
                )
                await db.commit()
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
        from app.services.log_writer import emit_log

        async with async_session() as db:
            await emit_log(
                db,
                source="worker",
                level="error",
                message=f"task_failed (http): {error[:500]}",
                worker_id=worker_id,
                task_id=task_id,
                details={"via": "http"},
            )
            await db.commit()
        return {"ok": True, "status": "failed", "task_id": task_id}

    raise HTTPException(400, f"Unsupported event type: {body.type}")


@router.get("/cse-key/{task_id}")
async def worker_cse_key(
    task_id: str,
    _: None = Depends(_verify_worker_token),
):
    """§10 CSE premium: ключ расшифровки из KMS компании (оркестратор — прокси)."""
    from app.services.cse_kms import fetch_worker_key_from_kms

    async with async_session() as db:
        result = await fetch_worker_key_from_kms(db, task_id=task_id)
    return result
