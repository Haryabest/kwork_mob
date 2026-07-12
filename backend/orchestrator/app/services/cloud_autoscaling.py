"""Облачные инстансы + авто-масштаб (§11.3.3 / §14.7) — сторона оркестратора."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AutoscalingRule, CloudCost, CloudInstanceRecord, CloudOperation, WorkerNode
from app.services.cloud_client import CloudProviderClient, cloud_user_data

logger = logging.getLogger(__name__)


def _client(provider: str) -> CloudProviderClient:
    return CloudProviderClient(
        provider,
        token=os.getenv("CLOUD_API_TOKEN") or getattr(settings, "CLOUD_API_TOKEN", "") or "",
        base_url=os.getenv("CLOUD_API_BASE") or getattr(settings, "CLOUD_API_BASE", None),
    )


async def list_flavors(provider: str) -> list[dict]:
    try:
        return _client(provider).list_flavors()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Cloud API: {exc}") from exc


async def create_cloud_workers(
    db: AsyncSession,
    *,
    provider: str,
    gpu: str,
    count: int,
    image: str | None,
    vcpus: int,
    ram_gb: int,
    triggered_by: str = "manual",
) -> list[dict]:
    count = max(1, min(count, 10))
    image = image or os.getenv("WORKER_DOCKER_IMAGE", "kwork-worker:latest")
    client = _client(provider)
    created = []
    ws_url = os.getenv(
        "ORCHESTRATOR_WS_PUBLIC",
        settings.API_BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/ws/worker",
    )
    for i in range(count):
        worker_id = f"cloud-{provider}-{gpu}-{int(datetime.now(timezone.utc).timestamp())}-{i}"
        ud = cloud_user_data(
            worker_id=worker_id,
            orchestrator_ws=ws_url,
            worker_token=os.getenv("WORKER_TOKEN", "worker-dev-token"),
            image_env={
                "CLOUD_PROVIDER": provider,
                "MINIO_ENDPOINT": settings.MINIO_ENDPOINT,
                "MINIO_ACCESS_KEY": settings.MINIO_ACCESS_KEY,
                "MINIO_SECRET_KEY": settings.MINIO_SECRET_KEY,
                "TAILSCALE_AUTH_KEY": os.getenv("TAILSCALE_AUTH_KEY", ""),
                "WORKER_DOCKER_IMAGE": image,
                "ORCHESTRATOR_WS_FALLBACK_URL": os.getenv("ORCHESTRATOR_WS_FALLBACK_URL", ""),
            },
        )
        try:
            inst = client.create_instance(
                gpu=gpu, image=image, worker_id=worker_id, vcpus=vcpus, ram_gb=ram_gb, user_data=ud
            )
            row = CloudInstanceRecord(
                provider=provider,
                instance_id=inst.id,
                worker_id=worker_id,
                gpu=gpu,
                status=inst.status,
                image=image,
                public_ip=inst.public_ip,
                tailscale_ip=inst.tailscale_ip,
                rub_per_hour=_estimate_rate(gpu),
                meta={"raw": inst.raw, "triggered_by": triggered_by},
            )
            db.add(row)
            db.add(
                CloudOperation(
                    provider=provider,
                    instance_id=inst.id,
                    action="create",
                    ok=True,
                    details={"worker_id": worker_id, "gpu": gpu},
                )
            )
            node = await db.get(WorkerNode, worker_id)
            if not node:
                node = WorkerNode(id=worker_id, status="starting", weight=0.0)
                db.add(node)
            node.meta = {
                **(node.meta or {}),
                "cloud": True,
                "provider": provider,
                "instance_id": inst.id,
                "gpu": gpu,
            }
            created.append(
                {
                    "worker_id": worker_id,
                    "instance_id": inst.id,
                    "status": inst.status,
                    "tailscale_ip": inst.tailscale_ip,
                    "public_ip": inst.public_ip,
                }
            )
        except Exception as exc:  # noqa: BLE001
            db.add(
                CloudOperation(
                    provider=provider,
                    instance_id=None,
                    action="create",
                    ok=False,
                    details={"error": str(exc)[:500]},
                )
            )
            logger.exception("cloud create failed")
            raise HTTPException(502, f"Не удалось создать инстанс: {exc}") from exc
    await db.flush()
    return created


def _estimate_rate(gpu: str) -> int:
    rates = {"rtx4090": 120, "a100": 280, "l40s": 220, "a6000": 200}
    return rates.get(gpu.lower(), int(os.getenv("CLOUD_DEFAULT_RUB_HOUR", "150")))


async def start_instance(db: AsyncSession, instance_id: str) -> dict:
    row = await db.scalar(select(CloudInstanceRecord).where(CloudInstanceRecord.instance_id == instance_id))
    if not row:
        raise HTTPException(404, "Инстанс не найден")
    client = _client(row.provider)
    try:
        inst = client.start_instance(instance_id)
        row.status = inst.status
        row.tailscale_ip = inst.tailscale_ip or row.tailscale_ip
        row.public_ip = inst.public_ip or row.public_ip
        db.add(CloudOperation(provider=row.provider, instance_id=instance_id, action="start", ok=True, details={}))
        await db.flush()
        return {"instance_id": instance_id, "status": row.status}
    except Exception as exc:  # noqa: BLE001
        db.add(
            CloudOperation(
                provider=row.provider, instance_id=instance_id, action="start", ok=False, details={"error": str(exc)[:300]}
            )
        )
        raise HTTPException(502, str(exc)) from exc


async def stop_instance(db: AsyncSession, instance_id: str) -> dict:
    row = await db.scalar(select(CloudInstanceRecord).where(CloudInstanceRecord.instance_id == instance_id))
    if not row:
        raise HTTPException(404, "Инстанс не найден")
    client = _client(row.provider)
    try:
        res = client.stop_instance(instance_id)
        started = row.started_at or row.created_at
        hours = max((datetime.now(timezone.utc) - started).total_seconds() / 3600.0, 0.01)
        cost = int(round(hours * (row.rub_per_hour or 0)))
        db.add(
            CloudCost(
                provider=row.provider,
                instance_id=instance_id,
                worker_id=row.worker_id,
                gpu=row.gpu,
                hours=hours,
                amount_rub=cost,
            )
        )
        row.status = "stopped"
        row.stopped_at = datetime.now(timezone.utc)
        node = await db.get(WorkerNode, row.worker_id)
        if node:
            node.status = "offline"
        db.add(
            CloudOperation(
                provider=row.provider, instance_id=instance_id, action="stop", ok=True, details={"cost_rub": cost, "res": res}
            )
        )
        await db.flush()
        return {"instance_id": instance_id, "status": "stopped", "cost_rub": cost}
    except Exception as exc:  # noqa: BLE001
        db.add(
            CloudOperation(
                provider=row.provider, instance_id=instance_id, action="stop", ok=False, details={"error": str(exc)[:300]}
            )
        )
        raise HTTPException(502, str(exc)) from exc


async def list_instances(db: AsyncSession) -> list[dict]:
    rows = (await db.scalars(select(CloudInstanceRecord).order_by(CloudInstanceRecord.id.desc()).limit(100))).all()
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "instance_id": r.instance_id,
            "worker_id": r.worker_id,
            "gpu": r.gpu,
            "status": r.status,
            "tailscale_ip": r.tailscale_ip,
            "public_ip": r.public_ip,
            "rub_per_hour": r.rub_per_hour,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "stopped_at": r.stopped_at.isoformat() if r.stopped_at else None,
        }
        for r in rows
    ]


async def upsert_rule(db: AsyncSession, data: dict) -> AutoscalingRule:
    rule_id = data.get("id")
    if rule_id:
        row = await db.get(AutoscalingRule, int(rule_id))
        if not row:
            raise HTTPException(404, "Правило не найдено")
    else:
        row = AutoscalingRule(name=data["name"])
        db.add(row)
    for field in (
        "name",
        "queue_threshold",
        "launch_count",
        "provider",
        "gpu",
        "image",
        "idle_timeout_min",
        "max_cloud_workers",
        "is_active",
    ):
        if field in data and data[field] is not None:
            setattr(row, field, data[field])
    await db.flush()
    return row


async def list_rules(db: AsyncSession) -> list[dict]:
    rows = (await db.scalars(select(AutoscalingRule).order_by(AutoscalingRule.id))).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "queue_threshold": r.queue_threshold,
            "launch_count": r.launch_count,
            "provider": r.provider,
            "gpu": r.gpu,
            "image": r.image,
            "idle_timeout_min": r.idle_timeout_min,
            "max_cloud_workers": r.max_cloud_workers,
            "is_active": r.is_active,
        }
        for r in rows
    ]


async def run_autoscaling_once(db: AsyncSession) -> dict:
    """Проверка правил каждые 30с (Celery)."""
    from app.services.queue import queue_service

    lengths = await queue_service.queue_lengths()
    total_q = int(lengths.get("normal", 0) or 0) + int(lengths.get("high", 0) or 0)
    active_cloud = await db.scalar(
        select(func.count())
        .select_from(CloudInstanceRecord)
        .where(CloudInstanceRecord.status.in_(("running", "starting", "active", "READY", "ready")))
    )
    active_cloud = int(active_cloud or 0)
    rules = (await db.scalars(select(AutoscalingRule).where(AutoscalingRule.is_active.is_(True)))).all()
    launched = 0
    stopped = 0
    for rule in rules:
        if total_q > rule.queue_threshold and active_cloud < rule.max_cloud_workers:
            need = min(rule.launch_count, rule.max_cloud_workers - active_cloud)
            if need > 0:
                created = await create_cloud_workers(
                    db,
                    provider=rule.provider,
                    gpu=rule.gpu,
                    count=need,
                    image=rule.image,
                    vcpus=8,
                    ram_gb=32,
                    triggered_by=f"autoscaling:{rule.id}",
                )
                launched += len(created)
                active_cloud += len(created)
                logger.info(
                    "cloud_autoscaling_triggered rule=%s queue=%s launched=%s",
                    rule.id,
                    total_q,
                    len(created),
                )
    # idle stop: облачные воркеры без heartbeat дольше idle_timeout
    now = datetime.now(timezone.utc)
    idle_min = min((r.idle_timeout_min for r in rules), default=30) if rules else 30
    cloud_rows = (
        await db.scalars(
            select(CloudInstanceRecord).where(CloudInstanceRecord.status.in_(("running", "active", "ready")))
        )
    ).all()
    for row in cloud_rows:
        node = await db.get(WorkerNode, row.worker_id)
        last = node.last_heartbeat if node else None
        if last and (now - last).total_seconds() > idle_min * 60 and total_q == 0:
            try:
                await stop_instance(db, row.instance_id)
                stopped += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("idle stop %s: %s", row.instance_id, exc)
            # stop one per cycle (TZ: interval)
            break

    await db.commit()
    return {"queue": total_q, "active_cloud": active_cloud, "launched": launched, "stopped": stopped}


async def cost_summary(db: AsyncSession) -> dict:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    month = today.replace(day=1)
    day_sum = await db.scalar(
        select(func.coalesce(func.sum(CloudCost.amount_rub), 0)).where(CloudCost.created_at >= today)
    )
    month_sum = await db.scalar(
        select(func.coalesce(func.sum(CloudCost.amount_rub), 0)).where(CloudCost.created_at >= month)
    )
    running = (
        await db.scalars(select(CloudInstanceRecord).where(CloudInstanceRecord.status.in_(("running", "active", "ready"))))
    ).all()
    burn = sum(r.rub_per_hour or 0 for r in running)
    return {
        "today_rub": int(day_sum or 0),
        "month_rub": int(month_sum or 0),
        "burn_rub_per_hour": burn,
        "running_instances": len(running),
    }
