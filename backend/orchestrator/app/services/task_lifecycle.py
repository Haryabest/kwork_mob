"""Жизненный цикл задачи: статусы заказа, Model3D, события WS."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import get_redis
from app.models import Model3D, Order, TaskQueue, WorkerNode
from app.services.events import publish_order_status
from app.services.queue import queue_service

logger = logging.getLogger(__name__)

MAX_QUALITY_GENERATION_ATTEMPTS = 3


async def _notify_order_user_push(
    db: AsyncSession,
    order: Order,
    *,
    pref_key: str,
    event_type: str,
    title: str,
    body: str,
    model_uuid: str | None = None,
) -> None:
    """Push B2C-владельцу заказа (§3.4.3)."""
    try:
        from app.models import User as UserModel
        from app.services import push as push_svc

        user = await db.get(UserModel, order.user_id)
        if not user:
            return
        prefs = dict(user.notification_prefs or {})
        if prefs.get(pref_key) is False:
            return
        if prefs.get("push_enabled") is False and prefs.get("email_enabled") is False:
            return
        if model_uuid:
            deeplink = f"kworkmob://open/models/{model_uuid}"
        else:
            deeplink = f"kworkmob://open/queue/{order.id}"
        data: dict[str, str] = {
            "type": event_type,
            "event": event_type,
            "order_id": str(order.id),
            "deeplink": deeplink,
        }
        if model_uuid:
            data["model_uuid"] = model_uuid
        await push_svc.send_to_user(
            db,
            user.id,
            title,
            body,
            data=data,
            email_fallback=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("order user push %s order=%s: %s", event_type, order.id, exc)


async def upsert_worker_heartbeat(
    db: AsyncSession,
    worker_id: str,
    *,
    status: str,
    gpu_name: str | None = None,
    gpu_load: float | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    from datetime import datetime, timezone

    node = await db.get(WorkerNode, worker_id)
    if not node:
        node = WorkerNode(id=worker_id)
        db.add(node)
    node.status = status
    if gpu_name is not None:
        node.gpu_name = gpu_name
    if gpu_load is not None:
        node.gpu_load = gpu_load
    node.last_heartbeat = datetime.now(timezone.utc)
    if meta:
        node.meta = {**(node.meta or {}), **meta}
    await db.commit()
    try:
        from app.services.events import publish_admin_dashboard

        await publish_admin_dashboard(
            {
                "type": "dashboard_refresh",
                "reason": "worker_heartbeat",
                "worker_id": worker_id,
                "status": status,
            }
        )
    except Exception:  # noqa: BLE001
        pass


async def mark_processing(db: AsyncSession, task_id: str, worker_id: str) -> Order | None:
    from datetime import datetime, timezone

    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    order = None
    if row:
        row.status = "processing"
        row.worker_id = worker_id
        row.processing_started_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        order = await db.get(Order, row.order_id)
        if order and order.status in ("queued", "paid"):
            order.status = "processing"
        if order:
            try:
                from app.services.user_events import record_event

                await record_event(
                    db,
                    event_type="order_created",
                    user_id=order.user_id,
                    company_id=order.company_id,
                    payload={"order_id": order.id, "task_id": task_id, "status": "processing"},
                )
            except Exception:  # noqa: BLE001
                pass
        await db.commit()
        if order:
            await publish_order_status(
                user_id=order.user_id,
                order_id=order.id,
                task_id=task_id,
                status="processing",
                extra={"worker_id": worker_id, "company_id": order.company_id},
            )
    return order


async def mark_completed(
    db: AsyncSession,
    *,
    task_id: str,
    glb_url: str,
    usdz_url: str | None = None,
    watermark_hmac: str | None = None,
) -> Order | None:
    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    if not row:
        return None
    row.status = "done"
    order = await db.get(Order, row.order_id)
    if not order:
        await db.commit()
        return None

    is_import = (row.payload_json or {}).get("pipeline") == "import_validate"
    order.status = "completed"
    file_digest: str | None = None
    if glb_url:
        try:
            from app.core.config import settings as cfg
            from app.services.integrity import sha256_bytes
            from app.services.minio import minio_service

            if glb_url.startswith("s3://"):
                bucket, _, key = glb_url[5:].partition("/")
            else:
                bucket, key = cfg.MINIO_BUCKET_MODELS, glb_url.lstrip("/")
            if bucket and key:
                file_digest = sha256_bytes(minio_service.download_bytes(bucket, key))
        except Exception:  # noqa: BLE001
            file_digest = None
    existing = await db.scalar(select(Model3D).where(Model3D.order_id == order.id))
    model_uuid: str | None = None
    if existing:
        existing.glb_url = glb_url
        if usdz_url:
            existing.usdz_url = usdz_url
        if watermark_hmac:
            existing.watermark_hmac = watermark_hmac
        if file_digest:
            existing.file_sha256 = file_digest
        if is_import:
            existing.publish_status = "imported"
        model_uuid = existing.uuid
    else:
        from app.services.model_storage import default_expires_at

        model_uuid = task_id
        db.add(
            Model3D(
                uuid=model_uuid,
                order_id=order.id,
                user_id=order.user_id,
                company_id=order.company_id,
                glb_url=glb_url,
                usdz_url=usdz_url,
                watermark_hmac=watermark_hmac,
                file_sha256=file_digest,
                publish_status="not_published",
                source_expires_at=default_expires_at(),
                display_name=order.model_display_name,
            )
        )
    await db.flush()
    if model_uuid:
        from app.services.publication_funnel import emit_funnel_ch_event

        emit_funnel_ch_event(
            model_uuid=model_uuid,
            event_type="generated",
            user_id=order.user_id,
            company_id=order.company_id,
        )
    try:
        from app.services import company_webhooks as wh

        await wh.emit(
            db,
            company_id=order.company_id,
            event="model.generated",
            payload={
                "order_id": order.id,
                "task_id": task_id,
                "glb_url": glb_url,
                "usdz_url": usdz_url,
            },
        )
        await wh.emit(
            db,
            company_id=order.company_id,
            event="order.completed",
            payload={"order_id": order.id, "task_id": task_id},
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.services import campaigns as camp_svc

        await camp_svc.on_order_completed(db, user_id=order.user_id, order_id=order.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("campaign nth_free hook: %s", exc)
    try:
        from app.services import company_notify as cn

        await cn.notify_company_event(
            db,
            company_id=order.company_id,
            event="generation_done",
            title="Генерация завершена",
            body=f"Заказ #{order.id} готов. Модель доступна для скачивания.",
            data={"order_id": str(order.id), "task_id": task_id},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("company notify generation_done: %s", exc)
    try:
        await _notify_order_user_push(
            db,
            order,
            pref_key="generation_done",
            event_type="generation_done",
            title="Модель готова",
            body=f"Заказ #{order.id} завершён.",
            model_uuid=model_uuid,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("user push generation_done: %s", exc)
    try:
        from app.services.user_events import record_event

        await record_event(
            db,
            event_type="model_generated",
            user_id=order.user_id,
            company_id=order.company_id,
            payload={"order_id": order.id, "task_id": task_id, "model_uuid": model_uuid},
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.services.marketplace_auto_upload import schedule_after_generation

        schedule_after_generation(
            order=order,
            model_uuid=model_uuid or task_id,
            payload=row.payload_json or {},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("marketplace auto upload schedule: %s", exc)
    await db.commit()
    await publish_order_status(
        user_id=order.user_id,
        order_id=order.id,
        task_id=task_id,
        status="completed",
        extra={"glb_url": glb_url, "company_id": order.company_id},
    )
    return order


async def handle_quality_gate_failure(db: AsyncSession, task_id: str, error: str) -> dict:
    """Quality gate fail: requeue до 3 попыток, refund только на финальной (§8.9.2)."""
    import json

    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    if not row:
        return {"action": "missing", "task_id": task_id}
    payload = dict(row.payload_json or {})
    attempts = int(payload.get("quality_attempts") or 0) + 1
    payload["quality_attempts"] = attempts
    row.payload_json = payload
    order = await db.get(Order, row.order_id)
    if attempts < MAX_QUALITY_GENERATION_ATTEMPTS:
        row.status = "queued"
        row.processing_started_at = None
        row.worker_id = None
        if order and order.status == "processing":
            order.status = "queued"
        await db.commit()
        redis = await get_redis()
        key = queue_service._key(row.priority)
        await redis.lpush(
            key,
            json.dumps(
                {"task_id": row.task_id, "order_id": row.order_id, "payload": payload},
                ensure_ascii=False,
            ),
        )
        if order:
            await publish_order_status(
                user_id=order.user_id,
                order_id=order.id,
                task_id=task_id,
                status="queued",
                extra={"quality_retry": attempts, "max_attempts": MAX_QUALITY_GENERATION_ATTEMPTS},
            )
        return {
            "action": "requeued",
            "attempt": attempts,
            "max_attempts": MAX_QUALITY_GENERATION_ATTEMPTS,
        }
    final_error = f"{error} (after {attempts} attempts)"
    failed_order = await mark_failed(db, task_id, final_error)
    return {
        "action": "failed",
        "attempt": attempts,
        "max_attempts": MAX_QUALITY_GENERATION_ATTEMPTS,
        "refunded": bool(failed_order and failed_order.amount > 0),
    }


async def mark_failed(db: AsyncSession, task_id: str, error: str) -> Order | None:
    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    if not row:
        return None
    row.status = "failed"
    order = await db.get(Order, row.order_id)
    refund_meta: dict | None = None
    nsfw_blocked = False
    if order and order.status not in ("cancelled", "completed"):
        order.status = "failed"
        payload = dict(row.payload_json or {})
        is_import = payload.get("pipeline") == "import_validate"
        if is_import:
            model = await db.scalar(select(Model3D).where(Model3D.order_id == order.id))
            if model:
                model.publish_status = "import_failed"
        if is_import and "import_nsfw_detected" in error:
            try:
                from app.models import User as UserModel
                from app.services.nsfw import nsfw_service

                user = await db.get(UserModel, order.user_id)
                if user:
                    await nsfw_service.block_order(
                        db,
                        order=order,
                        user=user,
                        result={
                            "confidence": 0.0,
                            "method": "import_glb_texture",
                            "trigger": error[:120],
                        },
                        refund=True,
                        charged=order.amount > 0,
                    )
                    nsfw_blocked = True
            except Exception as exc:  # noqa: BLE001
                logger.exception("import nsfw block task=%s: %s", task_id, exc)
        # §6.12: quality gate / фатальный fail → полный возврат
        if order.amount > 0 and not nsfw_blocked:
            try:
                from app.models import User as UserModel
                from app.services.refunds import refund_order

                user = await db.get(UserModel, order.user_id)
                refund_meta = await refund_order(
                    db,
                    order,
                    reason=f"task_failed: {error[:200]}",
                    user=user,
                    prefer_card=True,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("refund on mark_failed task=%s: %s", task_id, exc)
                refund_meta = {"refunded": False, "error": str(exc)[:200]}
    try:
        from app.services import company_webhooks as wh

        if order:
            await wh.emit(
                db,
                company_id=order.company_id,
                event="order.failed",
                payload={
                    "order_id": order.id,
                    "task_id": task_id,
                    "error": error[:500],
                    "refund": refund_meta,
                },
            )
    except Exception:  # noqa: BLE001
        pass
    if order:
        try:
            if nsfw_blocked:
                await _notify_order_user_push(
                    db,
                    order,
                    pref_key="nsfw_blocked",
                    event_type="nsfw_blocked",
                    title="NSFW-блокировка",
                    body=f"Импорт заказа #{order.id} отклонён из-за запрещённого контента.",
                )
            else:
                refunded = bool(refund_meta and refund_meta.get("refunded"))
                await _notify_order_user_push(
                    db,
                    order,
                    pref_key="refund" if refunded else "generation_done",
                    event_type="generation_failed",
                    title="Возврат средств" if refunded else "Ошибка генерации",
                    body=(
                        f"Заказ #{order.id} не выполнен. Средства возвращены."
                        if refunded
                        else f"Заказ #{order.id} не выполнен."
                    ),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("user push generation_failed: %s", exc)
    await db.commit()
    if order:
        await publish_order_status(
            user_id=order.user_id,
            order_id=order.id,
            task_id=task_id,
            status="failed",
            extra={"error": error[:500], "refund": refund_meta},
        )
    return order


async def requeue_task(task_id: str) -> None:
    """Вернуть задачу в Redis при обрыве воркера."""
    import json

    async with async_session() as db:
        row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
        if not row or row.status not in ("processing", "queued"):
            return
        order = await db.get(Order, row.order_id)
        if order and order.status in ("processing", "queued"):
            order.status = "queued"
        row.status = "queued"
        row.processing_started_at = None
        row.worker_id = None
        payload = row.payload_json or {}
        await db.commit()
        redis = await get_redis()
        key = queue_service._key(row.priority)
        await redis.lpush(
            key,
            json.dumps(
                {"task_id": row.task_id, "order_id": row.order_id, "payload": payload},
                ensure_ascii=False,
            ),
        )
        if order:
            await publish_order_status(
                user_id=order.user_id,
                order_id=order.id,
                task_id=task_id,
                status="queued",
                extra={"requeued": True},
            )


async def try_queue_awaiting_orders(db: AsyncSession, user_id: int) -> list[int]:
    """После пополнения баланса — поставить awaiting_payment в очередь."""
    from app.models import Transaction, User

    user = await db.get(User, user_id)
    if not user:
        return []
    orders = (
        await db.scalars(
            select(Order).where(Order.user_id == user_id, Order.status == "awaiting_payment").order_by(Order.id)
        )
    ).all()
    queued_ids: list[int] = []
    from app.services import photo_encryption as photo_enc
    from app.services.nsfw import nsfw_service

    for order in orders:
        if user.balance < order.amount:
            break
        enc_key = await photo_enc.get_key(order.task_uuid)
        nsfw = await nsfw_service.check_task_photos(
            order.task_uuid, decryption_key=enc_key
        )
        if nsfw.get("is_nsfw"):
            await nsfw_service.block_order(
                db, order=order, user=user, result=nsfw, refund=True, charged=False
            )
            continue
        user.balance -= order.amount
        db.add(
            Transaction(
                user_id=user.id,
                company_id=order.company_id,
                amount=-order.amount,
                tx_type="charge",
                description=f"Заказ #{order.id} (после оплаты)",
            )
        )
        order.status = "queued"
        payload = {
            "category": order.category,
            "tier": order.tier,
            "target_marketplace": getattr(order, "target_marketplace", None) or "ozon",
            "user_id": user.id,
            "photos_bucket": settings.MINIO_BUCKET_PHOTOS,
            "photos_prefix": f"photos/{order.task_uuid}/",
            "models_bucket": settings.MINIO_BUCKET_MODELS,
        }
        if enc_key:
            payload["photo_encryption_key"] = enc_key
            payload["photo_encryption_alg"] = photo_enc.ALGORITHM
        await queue_service.enqueue(
            db,
            task_id=order.task_uuid,
            order_id=order.id,
            company_id=order.company_id,
            payload=payload,
            priority="high" if order.tier == "large" else "normal",
        )
        queued_ids.append(order.id)
        await publish_order_status(
            user_id=user.id,
            order_id=order.id,
            task_id=order.task_uuid,
            status="queued",
        )
    await db.commit()
    return queued_ids


async def cancel_processing_order(db: AsyncSession, order: Order) -> None:
    """Отмена во время генерации — без возврата (§3.4.2)."""
    from app.services.worker_hub import worker_hub

    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == order.task_uuid))
    if row:
        row.status = "cancelled"
        if row.worker_id:
            conn = await worker_hub.get(row.worker_id)
            if conn:
                try:
                    await conn.websocket.send_json({"type": "stop", "task_id": order.task_uuid})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("worker stop on cancel failed: %s", exc)
    order.status = "cancelled"
    await db.flush()

