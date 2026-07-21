"""Prometheus + ClickHouse метрики §4.4 / §11.2 / §12."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy import func, select

from app.core.config import settings

logger = logging.getLogger(__name__)

ORDERS_TOTAL = Counter("kwork_orders_total", "Orders by status", ["status"])
PENDING_POLL_TOTAL = Counter(
    "kwork_pending_payment_poll_total",
    "Pending YooKassa poll outcomes §8",
    ["outcome"],
)
QUEUE_LENGTH = Gauge("kwork_queue_length", "Queue length", ["queue"])
WORKER_GPU_TEMP = Gauge("kwork_worker_gpu_temp", "Worker GPU temp C", ["worker_id"])
WORKER_GPU_UTIL = Gauge("kwork_worker_gpu_util", "Worker GPU util %", ["worker_id"])
TASK_DURATION = Histogram(
    "kwork_task_duration_seconds",
    "Task E2E duration",
    buckets=(30, 60, 90, 120, 180, 240, 300, 600),
)
ANALYTICS_CH_PENDING = Gauge(
    "kwork_analytics_ch_pending_sync",
    "Mobile analytics PG rows not yet mirrored to ClickHouse §19.20",
)

_ch_client = None


def prometheus_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def record_pending_poll(stats: dict[str, int]) -> None:
    """Prometheus: исходы Celery poll_waiting_capture_pending §8."""
    for outcome, count in stats.items():
        n = int(count or 0)
        if n > 0:
            PENDING_POLL_TOTAL.labels(outcome=outcome).inc(n)


def record_analytics_ch_pending(count: int) -> None:
    ANALYTICS_CH_PENDING.set(int(count or 0))


def _ch():
    global _ch_client
    if _ch_client is not None:
        return _ch_client
    try:
        import clickhouse_connect

        _ch_client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=int(settings.CLICKHOUSE_PORT),
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD or "",
            database=settings.CLICKHOUSE_DB,
        )
        return _ch_client
    except Exception as exc:  # noqa: BLE001
        logger.debug("ClickHouse unavailable: %s", exc)
        _ch_client = False
        return None


def record_worker_metrics(worker_id: str, gpu: dict[str, Any], cpu: float, ram: float) -> None:
    temp = float(gpu.get("gpu_temp") or 0)
    util = float(gpu.get("gpu_util") or gpu.get("utilization") or 0)
    WORKER_GPU_TEMP.labels(worker_id=worker_id).set(temp)
    WORKER_GPU_UTIL.labels(worker_id=worker_id).set(util)
    client = _ch()
    if not client:
        return
    try:
        client.insert(
            "worker_metrics_minute",
            [
                [
                    datetime.now(timezone.utc).replace(tzinfo=None),
                    worker_id,
                    util,
                    float(gpu.get("vram_used_gb") or 0),
                    temp,
                    cpu,
                    ram,
                ]
            ],
            column_names=[
                "timestamp",
                "worker_id",
                "gpu_util",
                "vram_used_gb",
                "gpu_temp",
                "cpu_percent",
                "ram_percent",
            ],
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("CH worker metrics: %s", exc)


def record_queue_length(queue_name: str, length: int, avg_wait: float = 0.0) -> None:
    QUEUE_LENGTH.labels(queue=queue_name).set(length)
    client = _ch()
    if not client:
        return
    try:
        client.insert(
            "queue_metrics_minute",
            [[datetime.now(timezone.utc).replace(tzinfo=None), queue_name, int(length), float(avg_wait)]],
            column_names=["timestamp", "queue_name", "length", "avg_wait_seconds"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("CH queue metrics: %s", exc)


def record_order_event(
    order_id: int,
    event_type: str,
    user_id: int,
    company_id: int | None = None,
    details: str = "",
) -> None:
    try:
        ORDERS_TOTAL.labels(status=event_type).inc()
    except Exception:  # noqa: BLE001
        pass
    client = _ch()
    if not client:
        return
    try:
        client.insert(
            "order_events",
            [
                [
                    datetime.now(timezone.utc).replace(tzinfo=None),
                    int(order_id),
                    event_type,
                    int(user_id),
                    int(company_id) if company_id else None,
                    details[:500],
                ]
            ],
            column_names=["timestamp", "order_id", "event_type", "user_id", "company_id", "details"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("CH order event: %s", exc)


    except Exception as exc:  # noqa: BLE001
        logger.debug("CH order event: %s", exc)


def record_publication_funnel_event(
    *,
    model_uuid: str,
    event_type: str,
    user_id: int,
    company_id: int | None = None,
    marketplace: str | None = None,
) -> None:
    client = _ch()
    if not client:
        return
    try:
        client.insert(
            "publication_funnel_events",
            [
                [
                    datetime.now(timezone.utc).replace(tzinfo=None),
                    model_uuid[:64],
                    event_type[:32],
                    int(user_id),
                    int(company_id) if company_id else None,
                    (marketplace or "")[:16] or None,
                ]
            ],
            column_names=[
                "timestamp",
                "model_uuid",
                "event_type",
                "user_id",
                "company_id",
                "marketplace",
            ],
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("CH publication funnel: %s", exc)


def _ch_publication_funnel_live() -> dict[str, Any]:
    client = _ch()
    if not client:
        return {"source": "postgresql", "events_30d": {}}
    try:
        rows = client.query(
            "SELECT event_type, count() FROM publication_funnel_events "
            "WHERE timestamp > now() - INTERVAL 30 DAY GROUP BY event_type"
        ).result_rows
        events = {str(r[0]): int(r[1]) for r in rows}
        return {"source": "clickhouse", "events_30d": events}
    except Exception as exc:  # noqa: BLE001
        logger.debug("CH publication funnel query: %s", exc)
        return {"source": "postgresql", "events_30d": {}, "error": str(exc)}


async def _publication_funnel_dashboard() -> dict[str, Any]:
    from app.core.database import async_session
    from app.services import publication_funnel as funnel_svc

    since = datetime.now(timezone.utc) - timedelta(days=30)
    async with async_session() as db:
        pg = await funnel_svc.global_funnel(db, date_from=since, date_to=None)
        await db.commit()
    ch = _ch_publication_funnel_live()
    return {
        "source": ch.get("source") if ch.get("events_30d") else "postgresql",
        "period": pg.get("period"),
        "funnel": pg.get("funnel"),
        "by_segment": pg.get("by_segment"),
        "by_category": pg.get("by_category"),
        "live": ch,
    }


async def _pg_dashboard() -> dict:
    """Агрегаты из PostgreSQL (§11.2) — fallback и дополнение к ClickHouse."""
    from app.core.database import async_session
    from app.models import Company, CompanyMember, ModelFeedback, NsfwBlock, Order, ServiceLogEvent, TaskQueue, Transaction

    since = datetime.now(timezone.utc) - timedelta(days=7)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    paid_like = ("paid", "queued", "processing", "completed", "done")

    async with async_session() as db:
        status_rows = (
            await db.execute(select(Order.status, func.count()).group_by(Order.status))
        ).all()
        by_status = {r[0]: int(r[1]) for r in status_rows}

        revenue_today = int(
            await db.scalar(
                select(func.coalesce(func.sum(Order.amount), 0)).where(
                    Order.created_at >= today, Order.status.in_(paid_like)
                )
            )
            or 0
        )
        revenue_7d = int(
            await db.scalar(
                select(func.coalesce(func.sum(Order.amount), 0)).where(
                    Order.created_at >= since, Order.status.in_(paid_like)
                )
            )
            or 0
        )
        refunds = int(
            await db.scalar(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.created_at >= since,
                    Transaction.tx_type == "refund",
                )
            )
            or 0
        )
        upsell_revenue_7d = int(
            await db.scalar(
                select(func.coalesce(func.sum(Order.upsell_amount), 0)).where(
                    Order.created_at >= since, Order.status.in_(paid_like)
                )
            )
            or 0
        )
        nsfw_withheld_7d = int(
            await db.scalar(
                select(func.coalesce(func.sum(Order.amount), 0))
                .select_from(NsfwBlock)
                .join(Order, Order.id == NsfwBlock.order_id)
                .where(
                    NsfwBlock.created_at >= since,
                    NsfwBlock.refunded.is_(False),
                )
            )
            or 0
        )

        queued = int(
            await db.scalar(select(func.count()).select_from(TaskQueue).where(TaskQueue.status == "queued"))
            or 0
        )
        processing = int(
            await db.scalar(
                select(func.count()).select_from(TaskQueue).where(TaskQueue.status == "processing")
            )
            or 0
        )

        ewt_normal = await db.scalar(
            select(func.avg(func.extract("epoch", func.now() - TaskQueue.created_at))).where(
                TaskQueue.status == "queued", TaskQueue.priority == "normal"
            )
        )
        ewt_high = await db.scalar(
            select(func.avg(func.extract("epoch", func.now() - TaskQueue.created_at))).where(
                TaskQueue.status == "queued", TaskQueue.priority == "high"
            )
        )

        rating_rows = (
            await db.execute(select(ModelFeedback.rating, func.count()).group_by(ModelFeedback.rating))
        ).all()
        rating_dist = {str(i): 0 for i in range(1, 6)}
        total_fb = 0
        high = 0
        for rating, cnt in rating_rows:
            rating_dist[str(int(rating))] = int(cnt)
            total_fb += int(cnt)
            if int(rating) >= 4:
                high += int(cnt)

        reason_rows = (
            await db.execute(select(ModelFeedback.reasons).where(ModelFeedback.rating <= 3).limit(500))
        ).scalars().all()
        reason_hist: dict[str, int] = {}
        for reasons in reason_rows:
            for r in reasons or []:
                key = str(r)
                reason_hist[key] = reason_hist.get(key, 0) + 1

        companies_active = int(
            await db.scalar(select(func.count()).select_from(Company).where(Company.status == "active"))
            or 0
        )
        photographers = int(
            await db.scalar(
                select(func.count()).select_from(CompanyMember).where(CompanyMember.role == "photographer")
            )
            or 0
        )

        top_companies = (
            await db.execute(
                select(Order.company_id, func.count(), func.coalesce(func.sum(Order.amount), 0))
                .where(Order.company_id.is_not(None), Order.created_at >= since)
                .group_by(Order.company_id)
                .order_by(func.sum(Order.amount).desc())
                .limit(10)
            )
        ).all()

        nsfw_blocked = int(by_status.get("nsfw_blocked", 0) + by_status.get("blocked_nsfw", 0))

        hour_bucket = func.date_trunc("hour", Order.created_at).label("hour_bucket")
        hourly = (
            await db.execute(
                select(hour_bucket, func.count())
                .where(Order.created_at >= datetime.now(timezone.utc) - timedelta(hours=48))
                .group_by(hour_bucket)
                .order_by(hour_bucket)
            )
        ).all()

        qs_logs = (
            await db.execute(
                select(ServiceLogEvent.details).where(
                    ServiceLogEvent.source == "worker",
                    ServiceLogEvent.message == "task_completed",
                    ServiceLogEvent.created_at >= since,
                    ServiceLogEvent.details.isnot(None),
                )
            )
        ).scalars().all()
        qs_scores: list[float] = []
        for details in qs_logs:
            if not details:
                continue
            raw = details.get("quality_score")
            if raw is None:
                continue
            try:
                qs_scores.append(float(raw))
            except (TypeError, ValueError):
                continue
        qs_pass = sum(1 for s in qs_scores if s >= 0.7)
        qs_pass_rate = round(qs_pass / max(len(qs_scores), 1), 4)

    return {
        "orders_by_status": by_status,
        "queued": queued,
        "processing": processing,
        "revenue_today_rub": revenue_today,
        "revenue_7d_rub": revenue_7d,
        "refunds_7d_rub": refunds,
        "upsell_revenue_7d_rub": upsell_revenue_7d,
        "nsfw_withheld_7d_rub": nsfw_withheld_7d,
        "ewt_normal_sec": float(ewt_normal or 0),
        "ewt_high_sec": float(ewt_high or 0),
        "rating_distribution": rating_dist,
        "rating_share_4_5": round(high / max(total_fb, 1), 4),
        "rating_total": total_fb,
        "low_rating_reasons": sorted(reason_hist.items(), key=lambda x: -x[1])[:20],
        "companies_active": companies_active,
        "photographers_active": photographers,
        "top_companies": [
            {"company_id": r[0], "orders": int(r[1]), "revenue_rub": int(r[2])} for r in top_companies
        ],
        "nsfw_blocked": nsfw_blocked,
        "orders_hourly": [
            {"hour": (r[0].isoformat() if r[0] else None), "count": int(r[1])} for r in hourly
        ],
        "qs_pass_rate_7d": qs_pass_rate,
        "qs_sample_total": len(qs_scores),
    }


async def dashboard_aggregates() -> dict:
    """Дашборд §11.2/§11.4: finance keys upsell_revenue_7d_rub, nsfw_withheld_7d_rub."""
    ch = {"source": "unavailable", "workers": [], "queues": []}
    client = _ch()
    if client:
        try:
            workers = client.query(
                "SELECT worker_id, avg(gpu_util), avg(gpu_temp), max(timestamp) "
                "FROM worker_metrics_minute WHERE timestamp > now() - INTERVAL 15 MINUTE "
                "GROUP BY worker_id ORDER BY worker_id"
            ).result_rows
            queues = client.query(
                "SELECT queue_name, argMax(length, timestamp), avg(avg_wait_seconds) "
                "FROM queue_metrics_minute WHERE timestamp > now() - INTERVAL 15 MINUTE "
                "GROUP BY queue_name"
            ).result_rows
            ch = {
                "source": "clickhouse",
                "workers": [
                    {
                        "worker_id": r[0],
                        "gpu_util": float(r[1] or 0),
                        "gpu_temp": float(r[2] or 0),
                        "last_seen": str(r[3]),
                    }
                    for r in workers
                ],
                "queues": [
                    {"queue": r[0], "length": int(r[1] or 0), "avg_wait": float(r[2] or 0)}
                    for r in queues
                ],
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("dashboard CH: %s", exc)
            ch = {"source": "error", "error": str(exc), "workers": [], "queues": []}

    try:
        pg = await _pg_dashboard()
    except Exception as exc:  # noqa: BLE001
        logger.warning("dashboard PG: %s", exc)
        pg = {"error": str(exc)}

    try:
        publication_funnel = await _publication_funnel_dashboard()
    except Exception as exc:  # noqa: BLE001
        logger.warning("dashboard funnel: %s", exc)
        publication_funnel = {"source": "error", "error": str(exc)}

    return {
        "source": ch.get("source"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workers": ch.get("workers", []),
        "queues": ch.get("queues", []),
        "ops": {
            "orders_by_status": pg.get("orders_by_status", {}),
            "queued": pg.get("queued", 0),
            "processing": pg.get("processing", 0),
            "ewt_normal_sec": pg.get("ewt_normal_sec", 0),
            "ewt_high_sec": pg.get("ewt_high_sec", 0),
            "orders_hourly": pg.get("orders_hourly", []),
        },
        "finance": {
            "revenue_today_rub": pg.get("revenue_today_rub", 0),
            "revenue_7d_rub": pg.get("revenue_7d_rub", 0),
            "refunds_7d_rub": pg.get("refunds_7d_rub", 0),
            "upsell_revenue_7d_rub": pg.get("upsell_revenue_7d_rub", 0),
            "nsfw_withheld_7d_rub": pg.get("nsfw_withheld_7d_rub", 0),
        },
        "b2b": {
            "companies_active": pg.get("companies_active", 0),
            "photographers_active": pg.get("photographers_active", 0),
            "top_companies": pg.get("top_companies", []),
        },
        "quality": {
            "rating_distribution": pg.get("rating_distribution", {}),
            "rating_share_4_5": pg.get("rating_share_4_5", 0),
            "rating_total": pg.get("rating_total", 0),
            "low_rating_reasons": pg.get("low_rating_reasons", []),
            "qs_pass_rate_7d": pg.get("qs_pass_rate_7d", 0),
            "qs_sample_total": pg.get("qs_sample_total", 0),
        },
        "moderation": {
            "nsfw_blocked": pg.get("nsfw_blocked", 0),
        },
        "publication_funnel": publication_funnel,
        "pg_error": pg.get("error"),
    }
