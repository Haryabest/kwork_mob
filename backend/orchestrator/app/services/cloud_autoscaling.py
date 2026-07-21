"""Облачные инстансы + авто-масштаб (§11.3.3 / §14.7) — сторона оркестратора."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AutoscalingRule, CloudCost, CloudInstanceRecord, CloudOperation, WorkerNode
from app.services.cloud_client import (
    PROVIDERS,
    CloudProviderClient,
    cloud_token,
    cloud_user_data,
)

logger = logging.getLogger(__name__)

PENDING_SCALE_KEY = "cloud:scale_pending"
IDLE_STOP_LAST_KEY = "cloud:idle_stop:last"


def _client(provider: str) -> CloudProviderClient:
    return CloudProviderClient(
        provider,
        token=cloud_token(provider) or getattr(settings, "CLOUD_API_TOKEN", "") or "",
        base_url=os.getenv(f"CLOUD_{provider.upper()}_API_BASE")
        or os.getenv("CLOUD_API_BASE")
        or getattr(settings, "CLOUD_API_BASE", None),
    )


async def list_flavors(provider: str) -> list[dict]:
    try:
        return _client(provider).list_flavors()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Cloud API: {exc}") from exc


def _estimate_rate(gpu: str) -> int:
    rates = {"rtx4090": 120, "a100": 280, "l40s": 220, "a6000": 200}
    return rates.get(gpu.lower(), int(os.getenv("CLOUD_DEFAULT_RUB_HOUR", "150")))


async def _budget_thresholds(db: AsyncSession) -> dict:
    from app.services import alert_thresholds as at

    return await at.load_thresholds(db)


async def _raw_cost_summary(db: AsyncSession) -> dict:
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


async def _hourly_cost_series(db: AsyncSession, hours: int = 24) -> list[dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        await db.execute(
            select(
                func.date_trunc("hour", CloudCost.created_at).label("h"),
                func.coalesce(func.sum(CloudCost.amount_rub), 0).label("rub"),
            )
            .where(CloudCost.created_at >= since)
            .group_by("h")
            .order_by("h")
        )
    ).all()
    return [{"hour": r.h.isoformat() if r.h else None, "rub": int(r.rub or 0)} for r in rows]


async def budget_status(db: AsyncSession) -> dict[str, Any]:
    """Сводка бюджета облака для admin / soft-launch §11.3.3."""
    costs = await _raw_cost_summary(db)
    th = await _budget_thresholds(db)
    monthly_limit = int(th.get("cloud_monthly_budget_rub") or 0)
    daily_limit = int(th.get("cloud_daily_budget_rub") or 0)
    burn_alert = int(th.get("cloud_burn_alert_rub_per_hour") or 0)
    month_rub = int(costs.get("month_rub") or 0)
    today_rub = int(costs.get("today_rub") or 0)
    burn = int(costs.get("burn_rub_per_hour") or 0)
    blocked = False
    reasons: list[str] = []
    if monthly_limit > 0 and month_rub >= monthly_limit:
        blocked = True
        reasons.append("monthly_budget_exceeded")
    if daily_limit > 0 and today_rub >= daily_limit:
        blocked = True
        reasons.append("daily_budget_exceeded")
    burn_over = burn_alert > 0 and burn > burn_alert
    hourly = await _hourly_cost_series(db)
    forecast_24h = burn * 24
    return {
        **costs,
        "cloud_monthly_budget_rub": monthly_limit,
        "cloud_daily_budget_rub": daily_limit,
        "cloud_burn_alert_rub_per_hour": burn_alert,
        "budget_blocked": blocked,
        "budget_block_reasons": reasons,
        "burn_over_alert_threshold": burn_over,
        "monthly_remaining_rub": max(monthly_limit - month_rub, 0) if monthly_limit > 0 else None,
        "daily_remaining_rub": max(daily_limit - today_rub, 0) if daily_limit > 0 else None,
        "forecast_24h_rub": forecast_24h,
        "hourly_cost_rub": hourly,
    }


async def _maybe_budget_alert(db: AsyncSession, *, reason: str, msg: str) -> None:
    from app.core.config import settings
    from app.services import alerts as alerts_svc

    cooldown = int(getattr(settings, "CLOUD_BUDGET_ALERT_COOLDOWN_SEC", 3600) or 3600)
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        key = f"cloud:budget_alert:{reason}"
        if await redis.get(key):
            return
        await redis.setex(key, cooldown, "1")
    except Exception:  # noqa: BLE001
        pass
    try:
        await alerts_svc.send_dual(
            db,
            msg,
            event_type="cloud_budget",
            payload={"reason": reason, "fingerprint": f"cloud_budget:{reason}"},
            subject="[3dvektor] Cloud GPU budget",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("cloud budget alert: %s", exc)


async def assert_cloud_budget_ok(
    db: AsyncSession,
    *,
    additional_rub_per_hour: int = 0,
    triggered_by: str = "manual",
) -> None:
    """Hard-stop: блок launch при превышении бюджета (§11.3.3 / soft-launch)."""
    status = await budget_status(db)
    burn = int(status.get("burn_rub_per_hour") or 0) + max(additional_rub_per_hour, 0)
    burn_alert = int(status.get("cloud_burn_alert_rub_per_hour") or 0)
    if status.get("budget_blocked"):
        reasons = status.get("budget_block_reasons") or []
        msg = (
            f"Cloud GPU budget hard-stop ({triggered_by}): "
            f"month={status.get('month_rub')}₽ / day={status.get('today_rub')}₽ · "
            f"burn={burn}₽/ч · reasons={','.join(reasons)}"
        )
        await _maybe_budget_alert(db, reason="hard_stop", msg=msg)
        raise HTTPException(
            402,
            detail={
                "code": "cloud_budget_exceeded",
                "message": "Лимит расходов на облачные GPU исчерпан",
                "budget": status,
            },
        )
    if burn_alert > 0 and burn > burn_alert:
        await _maybe_budget_alert(
            db,
            reason="burn_high",
            msg=(
                f"Cloud burn {burn}₽/ч > порог {burn_alert}₽/ч "
                f"(month {status.get('month_rub')}₽, today {status.get('today_rub')}₽)"
            ),
        )


async def create_cloud_workers(
    db: AsyncSession,
    *,
    provider: str,
    gpu: str,
    count: int,
    image: str | None,
    vcpus: int,
    ram_gb: int,
    flavor_id: int | None = None,
    os_id: int | None = None,
    ssd_gb: int | None = None,
    triggered_by: str = "manual",
) -> list[dict]:
    count = max(1, min(count, 10))
    est_burn = _estimate_rate(gpu) * count
    await assert_cloud_budget_ok(db, additional_rub_per_hour=est_burn, triggered_by=triggered_by)
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
                "WORKER_GIT_REPO": os.getenv("WORKER_GIT_REPO", ""),
                "WORKER_GIT_BRANCH": os.getenv("WORKER_GIT_BRANCH", "main"),
            },
        )
        try:
            inst = client.create_instance(
                gpu=gpu,
                image=image,
                worker_id=worker_id,
                vcpus=vcpus,
                ram_gb=ram_gb,
                user_data=ud,
                flavor_id=flavor_id,
                os_id=os_id,
                ssd_gb=ssd_gb,
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
                meta={
                    "raw": inst.raw,
                    "triggered_by": triggered_by,
                    "bootstrap_script": inst.bootstrap_script or ud,
                    "login": inst.login,
                },
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
                    "login": inst.login,
                    "bootstrap_hint": (
                        f"SSH {inst.login}@{inst.public_ip}, run bootstrap from meta.bootstrap_script"
                        if provider in PROVIDERS
                        else None
                    ),
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


async def terminate_instance(db: AsyncSession, instance_id: str) -> dict:
    """Остановить и удалить (terminate) облачный инстанс §11.3.3."""
    row = await db.scalar(select(CloudInstanceRecord).where(CloudInstanceRecord.instance_id == instance_id))
    if not row:
        raise HTTPException(404, "Инстанс не найден")
    client = _client(row.provider)
    try:
        res = client.stop_instance(instance_id, shelve=False)
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
        row.status = "terminated"
        row.stopped_at = datetime.now(timezone.utc)
        node = await db.get(WorkerNode, row.worker_id)
        if node:
            node.status = "offline"
        db.add(
            CloudOperation(
                provider=row.provider,
                instance_id=instance_id,
                action="terminate",
                ok=True,
                details={"cost_rub": cost, "res": res},
            )
        )
        await db.flush()
        return {"instance_id": instance_id, "status": "terminated", "cost_rub": cost}
    except Exception as exc:  # noqa: BLE001
        db.add(
            CloudOperation(
                provider=row.provider,
                instance_id=instance_id,
                action="terminate",
                ok=False,
                details={"error": str(exc)[:300]},
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
        "auto_launch",
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
            "auto_launch": r.auto_launch,
        }
        for r in rows
    ]


async def _get_pending_scale() -> dict | None:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        raw = await redis.get(PENDING_SCALE_KEY)
        if not raw:
            return None
        return json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception:  # noqa: BLE001
        return None


async def mark_scale_pending(*, queue: int, rule_id: int, reason: str) -> None:
    payload = {
        "queue": queue,
        "rule_id": rule_id,
        "reason": reason,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        await redis.setex(PENDING_SCALE_KEY, 3600, json.dumps(payload))
    except Exception as exc:  # noqa: BLE001
        logger.warning("mark_scale_pending: %s", exc)


async def clear_scale_pending() -> None:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        await redis.delete(PENDING_SCALE_KEY)
    except Exception:  # noqa: BLE001
        pass


async def scaling_owner_status(db: AsyncSession) -> dict[str, Any]:
    """Semi-auto owner loop §4.7: очередь, бюджет, pending approval."""
    from app.services.queue import queue_service
    from app.services.worker_hub import worker_hub

    lengths = await queue_service.queue_lengths()
    total_q = int(lengths.get("normal", 0) or 0) + int(lengths.get("high", 0) or 0)
    snap = await worker_hub.list_snapshot()
    live = [w for w in snap if w.get("status") not in ("offline",)]
    busy = sum(1 for w in live if w.get("status") in ("busy", "overheated", "processing"))
    online = len(live)
    all_busy = online > 0 and busy >= online
    pending = await _get_pending_scale()
    budget = await budget_status(db)
    return {
        "queue": total_q,
        "workers_online": online,
        "workers_busy": busy,
        "all_busy": all_busy,
        "pending_approval": pending is not None,
        "pending": pending,
        "budget": budget,
    }


async def approve_pending_scale(db: AsyncSession) -> dict[str, Any]:
    """Owner подтверждает запуск облачных воркеров (semi-auto §4.7)."""
    pending = await _get_pending_scale()
    if not pending:
        raise HTTPException(404, "Нет ожидающего запроса на масштабирование")
    rule_id = int(pending.get("rule_id") or 0)
    rule = await db.get(AutoscalingRule, rule_id) if rule_id else None
    if not rule:
        rules = (await db.scalars(select(AutoscalingRule).where(AutoscalingRule.is_active.is_(True)))).all()
        rule = rules[0] if rules else None
    if not rule:
        raise HTTPException(404, "Нет активного правила авто-масштаба")
    await clear_scale_pending()
    created = await create_cloud_workers(
        db,
        provider=rule.provider,
        gpu=rule.gpu,
        count=rule.launch_count,
        image=rule.image,
        vcpus=8,
        ram_gb=32,
        triggered_by=f"owner_approve:{rule.id}",
    )
    await _audit_scale_event(db, "cloud_scale_approved", rule_id=rule.id, launched=len(created))
    await db.commit()
    return {"launched": len(created), "rule_id": rule.id, "items": created}


async def _audit_scale_event(db: AsyncSession, action: str, **details: Any) -> None:
    try:
        from app.services.log_writer import emit_log

        await emit_log(
            db,
            source="cloud_autoscaling",
            level="INFO",
            message=action,
            details=details,
        )
    except Exception:  # noqa: BLE001
        pass


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
    pending_set = False
    for rule in rules:
        if total_q > rule.queue_threshold and active_cloud < rule.max_cloud_workers:
            need = min(rule.launch_count, rule.max_cloud_workers - active_cloud)
            if need > 0:
                if not rule.auto_launch:
                    await mark_scale_pending(queue=total_q, rule_id=rule.id, reason="queue_threshold")
                    pending_set = True
                    await _audit_scale_event(
                        db,
                        "cloud_autoscaling_pending",
                        rule_id=rule.id,
                        queue=total_q,
                        need=need,
                    )
                    break
                try:
                    await assert_cloud_budget_ok(
                        db,
                        additional_rub_per_hour=_estimate_rate(rule.gpu) * need,
                        triggered_by=f"autoscaling:{rule.id}",
                    )
                except HTTPException:
                    logger.warning(
                        "cloud_autoscaling_budget_blocked rule=%s queue=%s",
                        rule.id,
                        total_q,
                    )
                    break
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
                await _audit_scale_event(
                    db,
                    "cloud_autoscaling_triggered",
                    rule_id=rule.id,
                    queue=total_q,
                    launched=len(created),
                )
                logger.info(
                    "cloud_autoscaling_triggered rule=%s queue=%s launched=%s",
                    rule.id,
                    total_q,
                    len(created),
                )
    # idle stop: облачные воркеры без heartbeat дольше idle_timeout
    now = datetime.now(timezone.utc)
    idle_min = min((r.idle_timeout_min for r in rules), default=30) if rules else 30
    stop_interval_min = int(getattr(settings, "CLOUD_IDLE_STOP_INTERVAL_MIN", 5) or 5)
    try:
        from app.services.alert_thresholds import threshold_async

        stop_interval_min = int(await threshold_async("cloud_idle_stop_interval_min", stop_interval_min))
    except Exception:  # noqa: BLE001
        pass
    can_idle_stop = True
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        last_raw = await redis.get(IDLE_STOP_LAST_KEY)
        if last_raw:
            last_ts = float(last_raw.decode() if isinstance(last_raw, bytes) else last_raw)
            if (now.timestamp() - last_ts) < stop_interval_min * 60:
                can_idle_stop = False
    except Exception:  # noqa: BLE001
        pass
    cloud_rows = (
        await db.scalars(
            select(CloudInstanceRecord).where(CloudInstanceRecord.status.in_(("running", "active", "ready")))
        )
    ).all()
    if can_idle_stop:
        for row in cloud_rows:
            node = await db.get(WorkerNode, row.worker_id)
            last = node.last_heartbeat if node else None
            if last and (now - last).total_seconds() > idle_min * 60 and total_q == 0:
                try:
                    await stop_instance(db, row.instance_id)
                    stopped += 1
                    try:
                        from app.core.redis import get_redis

                        redis = await get_redis()
                        await redis.set(IDLE_STOP_LAST_KEY, str(now.timestamp()), ex=stop_interval_min * 60 + 60)
                    except Exception:  # noqa: BLE001
                        pass
                    await _audit_scale_event(db, "cloud_idle_stop", instance_id=row.instance_id)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("idle stop %s: %s", row.instance_id, exc)
                break

    await db.commit()
    return {
        "queue": total_q,
        "active_cloud": active_cloud,
        "launched": launched,
        "stopped": stopped,
        "pending_approval": pending_set,
    }


async def cost_summary(db: AsyncSession) -> dict:
    return await budget_status(db)
