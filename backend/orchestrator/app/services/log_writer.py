"""Запись централизованных логов (§11.5 / §9.3): ClickHouse service_logs + PG fallback."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

_ch_client = None


def _ch():
    global _ch_client
    if _ch_client is not None:
        return _ch_client if _ch_client is not False else None
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
        logger.debug("ClickHouse log writer unavailable: %s", exc)
        _ch_client = False
        return None


def _write_clickhouse(
    *,
    ts: datetime,
    source: str,
    level: str,
    message: str,
    worker_id: str | None = None,
    user_id: int | None = None,
    company_id: int | None = None,
    task_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    client = _ch()
    if not client:
        return
    try:
        client.insert(
            "service_logs",
            [
                [
                    ts.replace(tzinfo=None),
                    source,
                    level.upper(),
                    message[:4000],
                    worker_id or "",
                    user_id,
                    company_id,
                    task_id or "",
                    json.dumps(details or {}, ensure_ascii=False)[:8000],
                ]
            ],
            column_names=[
                "timestamp",
                "source",
                "level",
                "message",
                "worker_id",
                "user_id",
                "company_id",
                "task_id",
                "details",
            ],
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("ClickHouse service_logs insert failed: %s", exc)


async def emit_log(
    db: AsyncSession | None,
    *,
    source: str,
    level: str,
    message: str,
    worker_id: str | None = None,
    user_id: int | None = None,
    company_id: int | None = None,
    task_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Пишет в PG (service_log_events) и ClickHouse (service_logs)."""
    from app.models import ServiceLogEvent

    ts = datetime.now(timezone.utc)
    lvl = level.upper()
    msg = message[:4000]

    if db is not None:
        db.add(
            ServiceLogEvent(
                source=source,
                level=lvl,
                message=msg,
                worker_id=worker_id,
                user_id=user_id,
                company_id=company_id,
                task_id=task_id,
                details=details,
                created_at=ts,
            )
        )
        try:
            await db.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("PG service_log_events flush failed: %s", exc)

    _write_clickhouse(
        ts=ts,
        source=source,
        level=lvl,
        message=msg,
        worker_id=worker_id,
        user_id=user_id,
        company_id=company_id,
        task_id=task_id,
        details=details,
    )
