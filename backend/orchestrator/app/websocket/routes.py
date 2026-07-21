"""WebSocket: очередь для пользователей и воркеров."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import get_redis, release_task_lock
from app.core.security import TokenType, decode_token
from app.models import WorkerNode
from app.services.events import user_channel, admin_dashboard_channel
from app.services.queue import queue_service
from app.services.task_lifecycle import (
    handle_quality_gate_failure,
    mark_completed,
    mark_failed,
    mark_processing,
    requeue_task,
    upsert_worker_heartbeat,
)
from app.services.worker_hub import WorkerConnection, worker_hub

logger = logging.getLogger(__name__)
ws_router = APIRouter()


async def _worker_log(
    *,
    level: str,
    message: str,
    worker_id: str | None = None,
    task_id: str | None = None,
    details: dict | None = None,
) -> None:
    from app.services.log_writer import emit_log

    try:
        async with async_session() as db:
            await emit_log(
                db,
                source="worker",
                level=level,
                message=message,
                worker_id=worker_id,
                task_id=task_id,
                details=details,
            )
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug("worker log emit failed: %s", exc)


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
        payload = decode_token(token, TokenType.ACCESS)
        if int(payload.get("sub", 0)) != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
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


@ws_router.websocket("/ws/admin/dashboard")
async def admin_dashboard_ws(websocket: WebSocket):
    """Живые обновления admin dashboard §11.15 (воркеры, очередь, заказы)."""
    token = _extract_bearer(websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = decode_token(token, TokenType.ACCESS)
        if payload.get("role") != "admin":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    redis = await get_redis()
    pubsub = redis.pubsub()
    channel = admin_dashboard_channel()
    await pubsub.subscribe(channel)

    lengths = await queue_service.queue_lengths()
    await websocket.send_json(
        {
            "type": "connected",
            "queue": lengths,
            "ewt_sec": await queue_service.estimate_wait_time(lengths["normal"] + lengths["high"]),
        }
    )

    async def _reader():
        async for message in pubsub.listen():
            if message is None or message.get("type") != "message":
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

    async def _ticker():
        while True:
            await asyncio.sleep(10)
            lengths = await queue_service.queue_lengths()
            await websocket.send_json(
                {
                    "type": "dashboard_refresh",
                    "reason": "tick",
                    "queue": lengths,
                }
            )

    ticker = asyncio.create_task(_ticker())
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
        ticker.cancel()
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
                version = str(data.get("version") or data.get("trellis_version") or "")
                from app.services.trellis_rollout import is_version_allowed, normalize_version

                if version and not await is_version_allowed(version):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": "trellis_version_not_allowed",
                            "version": version,
                        }
                    )
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
                # повторный ready после охлаждения
                existing = await worker_hub.get(worker_id)
                if existing and existing.websocket is websocket:
                    await worker_hub.touch(worker_id, status="idle")
                    async with async_session() as db:
                        await upsert_worker_heartbeat(db, worker_id, status="idle")
                    await websocket.send_json({"type": "registered", "worker_id": worker_id})
                    await _worker_log(level="info", message="ready (reconnect)", worker_id=worker_id)
                    continue
                conn = WorkerConnection(
                    worker_id=worker_id,
                    websocket=websocket,
                    status="idle",
                    version=str(data.get("version") or data.get("trellis_version") or ""),
                    capabilities=list(data.get("capabilities") or []),
                    weight=float(data.get("weight") or 0),
                    meta={
                        "maintenance": bool((data.get("maintenance") or False)),
                        "docker_image": data.get("docker_image"),
                        "pipeline_mode": data.get("pipeline_mode"),
                    },
                )
                async with async_session() as db:
                    node = await db.get(WorkerNode, worker_id)
                    if node and node.meta:
                        conn.meta = {**conn.meta, **node.meta}
                    await upsert_worker_heartbeat(
                        db,
                        worker_id,
                        status="idle",
                        meta={
                            "version": conn.version,
                            "trellis_version": normalize_version(conn.version) or conn.version,
                            "capabilities": conn.capabilities,
                            "docker_image": (data.get("docker_image") or ""),
                            "pipeline_mode": data.get("pipeline_mode"),
                        },
                    )
                await worker_hub.register(conn)
                await websocket.send_json({"type": "registered", "worker_id": worker_id})
                await _worker_log(
                    level="info",
                    message=f"ready version={conn.version}",
                    worker_id=worker_id,
                    details={"capabilities": conn.capabilities},
                )
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
                # §12.4.1 / §13.4: GPU >85°C → Telegram + email
                try:
                    from app.services import gpu_thermal as thermal_svc

                    await thermal_svc.maybe_alert_from_metrics(
                        worker_id,
                        gpu if isinstance(gpu, dict) else {},
                        task_id=str(data.get("task_id") or getattr(conn, "current_task_id", None) or "")
                        or None,
                    )
                except Exception:  # noqa: BLE001
                    pass

            elif msg_type == "task_started":
                task_id = str(data.get("task_id") or "")
                if task_id:
                    await worker_hub.set_busy(worker_id, task_id)
                    async with async_session() as db:
                        await mark_processing(db, task_id, worker_id)
                    await _worker_log(
                        level="info",
                        message="task_started",
                        worker_id=worker_id,
                        task_id=task_id,
                    )

            elif msg_type == "already_processed":
                task_id = str(data.get("task_id") or "")
                result_url = str(data.get("result_url") or data.get("glb_url") or "")
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
                await websocket.send_json(
                    {
                        "type": "ack",
                        "of": "already_processed",
                        "task_id": task_id,
                        "result_url": (cached or {}).get("result_url") or result_url,
                    }
                )

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
                            await handle_quality_gate_failure(
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

                    from app.models import TaskQueue
                    from app.services import quality_alerts as qa

                    existing = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
                    if existing and existing.status == "done":
                        try:
                            from app.services import redlock_alerts as rl

                            await rl.notify_redlock_conflict(
                                task_id=task_id,
                                worker_id=worker_id,
                                reason="duplicate_completion",
                                details={"glb_url": glb_url},
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    else:
                        await mark_completed(
                            db,
                            task_id=task_id,
                            glb_url=glb_url,
                            usdz_url=data.get("usdz_url"),
                            watermark_hmac=data.get("watermark_hmac"),
                        )
                        try:
                            await qa.ingest_from_worker_event(db, task_id=task_id, data=data, failed=False)
                            await db.commit()
                        except Exception:  # noqa: BLE001
                            pass
                await release_task_lock(task_id)
                await worker_hub.set_idle(worker_id)
                await websocket.send_json({"type": "ack", "of": "task_completed", "task_id": task_id})
                await _worker_log(
                    level="info",
                    message="task_completed",
                    worker_id=worker_id,
                    task_id=task_id,
                    details={"glb_url": glb_url, "quality_score": quality_score},
                )

            elif msg_type == "segmentation_stats":
                task_id = str(data.get("task_id") or "")
                if task_id:
                    async with async_session() as db:
                        from app.services import quality_alerts as qa

                        await qa.ingest_from_worker_event(db, task_id=task_id, data=data)
                        await db.commit()
                await websocket.send_json({"type": "ack", "of": "segmentation_stats", "task_id": task_id})

            elif msg_type == "task_failed":
                task_id = str(data.get("task_id") or "")
                error = str(data.get("error") or "unknown")
                await release_task_lock(task_id)
                # failed_segmentation / transient — requeue с чекпоинтом; quality gate — fail
                if "quality_gate_failed" in error:
                    async with async_session() as db:
                        await handle_quality_gate_failure(db, task_id, error)
                elif "failed_segmentation" in error or data.get("checkpoint_path"):
                    async with async_session() as db:
                        from app.services import quality_alerts as qa

                        try:
                            await qa.ingest_from_worker_event(
                                db, task_id=task_id, data=data, failed=True
                            )
                            await db.commit()
                        except Exception:  # noqa: BLE001
                            pass
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
                await _worker_log(
                    level="error",
                    message=f"task_failed: {error[:500]}",
                    worker_id=worker_id,
                    task_id=task_id,
                )

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
                await _worker_log(
                    level="warning",
                    message=f"task_paused: {data.get('reason') or 'stop'}",
                    worker_id=worker_id,
                    task_id=task_id,
                    details={"checkpoint_path": cp},
                )

            elif msg_type == "overheating":
                temp = data.get("temp")
                await worker_hub.set_overheated(worker_id)
                async with async_session() as db:
                    await upsert_worker_heartbeat(
                        db, worker_id, status="overheated", meta={"temp": temp}
                    )
                await websocket.send_json({"type": "ack", "of": "overheating", "temp": temp})
                await _worker_log(
                    level="warning",
                    message=f"GPU overheating {temp}°C",
                    worker_id=worker_id,
                    task_id=str(data.get("task_id") or "") or None,
                    details={"temp": temp},
                )
                try:
                    from app.services import gpu_thermal as thermal_svc

                    await thermal_svc.maybe_alert_from_metrics(
                        worker_id,
                        {"gpu_temp": temp},
                        task_id=str(data.get("task_id") or "") or None,
                        force=True,
                    )
                except Exception:  # noqa: BLE001
                    pass

            elif msg_type == "task_conflict":
                task_id = str(data.get("task_id") or "")
                await worker_hub.set_idle(worker_id)
                if task_id:
                    await requeue_task(task_id)
                    try:
                        from app.services import redlock_alerts as rl

                        await rl.notify_redlock_conflict(
                            task_id=task_id,
                            worker_id=worker_id,
                            reason=str(data.get("reason") or "lock_not_acquired"),
                            conflict_with=str(data.get("conflict_with") or "") or None,
                        )
                    except Exception:  # noqa: BLE001
                        pass
                await websocket.send_json({"type": "ack", "of": "task_conflict"})
                await _worker_log(
                    level="warning",
                    message=f"task_conflict: {data.get('reason') or 'duplicate'}",
                    worker_id=worker_id,
                    task_id=task_id or None,
                )

            else:
                await websocket.send_json({"type": "ack", "of": msg_type})

    except WebSocketDisconnect:
        pass
    finally:
        if worker_id:
            removed = await worker_hub.unregister(worker_id, websocket)
            if removed and removed.current_task_id:
                async with async_session() as db:
                    from sqlalchemy import select

                    from app.models import TaskQueue

                    row = await db.scalar(
                        select(TaskQueue).where(TaskQueue.task_id == removed.current_task_id)
                    )
                    if row and row.status in ("queued", "processing"):
                        await requeue_task(removed.current_task_id)
            async with async_session() as db:
                await upsert_worker_heartbeat(db, worker_id, status="offline")
