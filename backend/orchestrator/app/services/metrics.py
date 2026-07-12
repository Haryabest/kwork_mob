"""Prometheus + ClickHouse метрики §4.4 / §12."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from app.core.config import settings

logger = logging.getLogger(__name__)

ORDERS_TOTAL = Counter("kwork_orders_total", "Orders by status", ["status"])
QUEUE_LENGTH = Gauge("kwork_queue_length", "Queue length", ["queue"])
WORKER_GPU_TEMP = Gauge("kwork_worker_gpu_temp", "Worker GPU temp C", ["worker_id"])
WORKER_GPU_UTIL = Gauge("kwork_worker_gpu_util", "Worker GPU util %", ["worker_id"])
TASK_DURATION = Histogram(
    "kwork_task_duration_seconds",
    "Task E2E duration",
    buckets=(30, 60, 90, 120, 180, 240, 300, 600),
)

_ch_client = None


def prometheus_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


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


async def dashboard_aggregates() -> dict:
    client = _ch()
    if not client:
        return {"source": "unavailable", "workers": [], "queues": []}
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
        return {
            "source": "clickhouse",
            "workers": [
                {"worker_id": r[0], "gpu_util": r[1], "gpu_temp": r[2], "last_seen": str(r[3])} for r in workers
            ],
            "queues": [{"queue": r[0], "length": r[1], "avg_wait": r[2]} for r in queues],
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("dashboard aggregates: %s", exc)
        return {"source": "error", "error": str(exc), "workers": [], "queues": []}
