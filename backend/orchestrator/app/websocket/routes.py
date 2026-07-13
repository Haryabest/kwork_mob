"""WebSocket: очередь для пользователей и воркеров."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import get_redis, release_task_lock
from app.core.security import TokenType
from app.services.events import user_channel
from app.services.queue import queue_service
from app.services.task_lifecycle import (
    mark_completed,
    mark_failed,
    requeue_task,
    upsert_worker_heartbeat,
)
from app.services.worker_hub import WorkerConnection, worker_hub

logger = logging.getLogger(__name__)
ws_router = APIRouter()


def _extract_bearer(websocket: WebSocket) -> str | None:
    auth = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return websocket.query_params.get("token")


@ws_router.websocket("/ws/queue/{user_id}")
async def queue_ws(websocket: WebSocket, user_id: int):
    """Обновления очереди / статуса заказа (Redis Pub/Sub)."""
    token = _extract_bearer(websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != TokenType.ACCESS.value:
            raise JWTError("bad type")
        if int(payload.get("sub", 0)) != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    redis = await get_redis()
    pubsub = redis.pubsub()
    channel = user_channel(user_id)
    await pubsub.subscribe(channel)

    lengths = await queue_service.queue_lengths()
    await websocket.send_json(
        {
            "type": "connected",
            "user_id": user_id,
            "queue": lengths,
            "ewt_sec": await queue_service.estimate_wait_time(lengths["normal"] + lengths["high"]),
        }
    )

    async def _reader():
        async for message in pubsub.listen():
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode()
            try:
                event = json.loads(data) if isinstance(data, str) else data
            except json.JSONDecodeError:
                continue
            await websocket.send_json(event)

    reader = asyncio.create_task(_reader())
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "ping":
                lengths = await queue_service.queue_lengths()
                await websocket.send_json({"type": "pong", "queue": lengths})
    except WebSocketDisconnect:
        pass
    finally:
        reader.cancel()
        await pubsub.unsubscribe(channel)
        await pubsub.close()


@ws_router.websocket("/ws/worker")
async def worker_ws(websocket: WebSocket):
    """Воркеры: ready, heartbeat, metrics, task_completed / failed."""
    token = _extract_bearer(websocket)
    if not token or token != settings.WORKER_TOKEN:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    worker_id: str | None = None
    conn: WorkerConnection | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "invalid_json"})
                continue

            msg_type = data.get("type")

            if msg_type == "ready":
                worker_id = str(data.get("worker_id") or "")
                if not worker_id:
                    await websocket.send_json({"type": "error", "error": "worker_id required"})
                    continue
                # повторный ready после охлаждения
                existing = await worker_hub.get(worker_id)
                if existing and existing.websocket is websocket:
                    await worker_hub.touch(worker_id, status="idle")
                    async with async_session() as db:
                        await upsert_worker_heartbeat(db, worker_id, status="idle")
                    await websocket.send_json({"type": "registered", "worker_id": worker_id})
                    continue
                conn = WorkerConnection(
                    worker_id=worker_id,
                    websocket=websocket,
                    status="idle",
                    version=str(data.get("version") or ""),
                    capabilities=list(data.get("capabilities") or []),
                    weight=float(data.get("weight") or 0),
                )
                await worker_hub.register(conn)
                async with async_session() as db:
                    await upsert_worker_heartbeat(
                        db,
                        worker_id,
                        status="idle",
                        meta={"version": conn.version, "capabilities": conn.capabilities},
                    )
                await websocket.send_json({"type": "registered", "worker_id": worker_id})
                continue

            if not worker_id or not conn:
                await websocket.send_json({"type": "error", "error": "send ready first"})
                continue

            if msg_type == "heartbeat":
                st = str(data.get("status") or conn.status)
                await worker_hub.touch(worker_id, status=st if st != "busy" else "busy")
                async with async_session() as db:
                    await upsert_worker_heartbeat(db, worker_id, status=st)
                await websocket.send_json({"type": "ack", "of": "heartbeat"})

            elif msg_type == "metrics":
                gpu = data.get("gpu") or {}
                await worker_hub.touch(
                    worker_id,
                    meta={"cpu": data.get("cpu_percent"), "ram": data.get("ram_percent"), "gpu": gpu},
                )
                async with async_session() as db:
                    await upsert_worker_heartbeat(
                        db,
                        worker_id,
                        status=conn.status,
                        gpu_name=str(gpu.get("name") or gpu.get("gpu_name") or "") or None,
                        gpu_load=float(gpu.get("gpu_util") or 0),
                        meta={"gpu": gpu},
                    )
                try:
                    from app.services.metrics import record_worker_metrics

                    record_worker_metrics(
                        worker_id,
                        gpu,
                        float(data.get("cpu_percent") or 0),
                        float(data.get("ram_percent") or 0),
                    )
                except Exception:  # noqa: BLE001
                    pass

            elif msg_type == "task_started":
                task_id = str(data.get("task_id") or "")
                if task_id:
                    await worker_hub.set_busy(worker_id, task_id)
                    async with async_session() as db:
                        await mark_processing(db, task_id, worker_id)

            elif msg_type == "task_completed":
                task_id = str(data.get("task_id") or "")
                glb_url = str(data.get("result_url") or data.get("glb_url") or "")
                quality_score = data.get("quality_score")
                threshold = float(os.getenv("QUALITY_THRESHOLD", "0.7"))
                if quality_score is not None:
                    try:
                        qs = float(quality_score)
                    except (TypeError, ValueError):
                        qs = None
                    if qs is not None and qs < threshold:
                        async with async_session() as db:
                            await mark_failed(
                                db,
                                task_id,
                                f"quality_gate_failed score={qs} < {threshold}",
                            )
                        await release_task_lock(task_id)
                        await worker_hub.set_idle(worker_id)
                        await websocket.send_json(
                            {"type": "ack", "of": "task_completed", "task_id": task_id, "rejected": "quality"}
                        )
                        continue
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
                                details={"glb_url": glb_url},
                            )
                        )
                        await db.commit()
                    else:
                        await mark_completed(
                            db,
                            task_id=task_id,
                            glb_url=glb_url,
                            usdz_url=data.get("usdz_url"),
                            watermark_hmac=data.get("watermark_hmac"),
                        )
                await release_task_lock(task_id)
                await worker_hub.set_idle(worker_id)
                await websocket.send_json({"type": "ack", "of": "task_completed", "task_id": task_id})

            elif msg_type == "task_failed":
                task_id = str(data.get("task_id") or "")
                error = str(data.get("error") or "unknown")
                await release_task_lock(task_id)
                # failed_segmentation / transient — requeue с чекпоинтом; quality gate — fail
                if "quality_gate_failed" in error:
                    async with async_session() as db:
                        await mark_failed(db, task_id, error)
                elif "failed_segmentation" in error or data.get("checkpoint_path"):
                    if data.get("checkpoint_path"):
                        async with async_session() as db:
                            from sqlalchemy import select

                            from app.models import TaskQueue

                            row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
                            if row:
                                payload = dict(row.payload_json or {})
                                payload["checkpoint_path"] = data["checkpoint_path"]
                                row.payload_json = payload
                                await db.commit()
                    await requeue_task(task_id)
                else:
                    async with async_session() as db:
                        await mark_failed(db, task_id, error)
                await worker_hub.set_idle(worker_id)
                await websocket.send_json({"type": "ack", "of": "task_failed", "task_id": task_id})

            elif msg_type == "task_paused":
                task_id = str(data.get("task_id") or "")
                cp = data.get("checkpoint_path")
                await release_task_lock(task_id)
                if task_id and cp:
                    async with async_session() as db:
                        from sqlalchemy import select

                        from app.models import TaskQueue

                        row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
                        if row:
                            payload = dict(row.payload_json or {})
                            payload["checkpoint_path"] = cp
                            row.payload_json = payload
                            await db.commit()
                if task_id:
                    await requeue_task(task_id)
                await worker_hub.set_idle(worker_id)
                await websocket.send_json({"type": "ack", "of": "task_paused", "task_id": task_id})

            elif msg_type == "overheating":
                temp = data.get("temp")
                await worker_hub.set_overheated(worker_id)
                async with async_session() as db:
                    await upsert_worker_heartbeat(
                        db, worker_id, status="overheated", meta={"temp": temp}
                    )
                await websocket.send_json({"type": "ack", "of": "overheating", "temp": temp})

            elif msg_type == "task_conflict":
                task_id = str(data.get("task_id") or "")
                await worker_hub.set_idle(worker_id)
                if task_id:
                    await requeue_task(task_id)
                await websocket.send_json({"type": "ack", "of": "task_conflict"})

            else:
                await websocket.send_json({"type": "ack", "of": msg_type})

    except WebSocketDisconnect:
        pass
    finally:
        if worker_id:
            removed = await worker_hub.unregister(worker_id, websocket)
            if removed and removed.current_task_id:
                await requeue_task(removed.current_task_id)
            async with async_session() as db:
                await upsert_worker_heartbeat(db, worker_id, status="offline")
