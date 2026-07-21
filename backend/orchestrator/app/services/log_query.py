"""Чтение логов для /admin/logs (§11.5): ClickHouse → PG → dev mock."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog, ServiceLogEvent
from app.services.log_writer import _ch

logger = logging.getLogger(__name__)

VALID_SOURCES = {"worker", "api", "audit", "orchestrator", "segmentation", "all"}
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "all"}


def _parse_dt(value: str | None, *, default: datetime | None = None) -> datetime | None:
    if not value:
        return default
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return default


def _row(
    *,
    ts: datetime,
    source: str,
    level: str,
    message: str,
    worker_id: str | None = None,
    user_id: int | None = None,
    company_id: int | None = None,
    task_id: str | None = None,
    details: Any = None,
    log_id: str | None = None,
) -> dict[str, Any]:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return {
        "id": log_id,
        "timestamp": ts.isoformat(),
        "source": source,
        "level": level.upper(),
        "message": message,
        "worker_id": worker_id,
        "user_id": user_id,
        "company_id": company_id,
        "task_id": task_id,
        "details": details,
    }


def _mock_logs(limit: int) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    samples = [
        ("orchestrator", "INFO", "Оркестратор запущен (dev mock — подключите ClickHouse/PostgreSQL)"),
        ("api", "INFO", "GET /health 200"),
        ("worker", "INFO", "worker-local-gpu-01 ready pipeline_mode=trellis"),
        ("worker", "WARNING", "GPU temp 82°C — близко к порогу"),
        ("audit", "INFO", "member.invite company_id=1"),
    ]
    items = []
    for i, (src, lvl, msg) in enumerate(samples[:limit]):
        items.append(
            _row(
                ts=now - timedelta(minutes=i * 3),
                source=src,
                level=lvl,
                message=msg,
                log_id=f"mock-{i}",
            )
        )
    return items


def _query_clickhouse(
    *,
    source: str | None,
    level: str | None,
    q: str | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
    limit: int,
) -> list[dict[str, Any]] | None:
    client = _ch()
    if not client:
        return None

    clauses = ["1=1"]
    params: dict[str, Any] = {"limit": limit}

    if from_dt:
        clauses.append("timestamp >= {from_ts:DateTime}")
        params["from_ts"] = from_dt.replace(tzinfo=None)
    if to_dt:
        clauses.append("timestamp <= {to_ts:DateTime}")
        params["to_ts"] = to_dt.replace(tzinfo=None)
    if source and source != "all":
        clauses.append("source = {source:String}")
        params["source"] = source
    if level and level.lower() != "all":
        clauses.append("level = {level:String}")
        params["level"] = level.upper()
    if q:
        clauses.append(
            "(positionCaseInsensitive(message, {q_raw:String}) > 0 "
            "OR positionCaseInsensitive(worker_id, {q_raw:String}) > 0 "
            "OR positionCaseInsensitive(task_id, {q_raw:String}) > 0)"
        )
        params["q_raw"] = q

    sql = f"""
        SELECT timestamp, source, level, message, worker_id, user_id, company_id, task_id, details
        FROM service_logs
        WHERE {" AND ".join(clauses)}
        ORDER BY timestamp DESC
        LIMIT {{limit:UInt32}}
    """
    try:
        result = client.query(sql, parameters=params)
        items: list[dict[str, Any]] = []
        for row in result.result_rows:
            ts, src, lvl, msg, wid, uid, cid, tid, det = row
            details = None
            if det:
                try:
                    details = json.loads(det) if isinstance(det, str) else det
                except json.JSONDecodeError:
                    details = {"raw": str(det)[:500]}
            items.append(
                _row(
                    ts=ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts)),
                    source=str(src),
                    level=str(lvl),
                    message=str(msg),
                    worker_id=str(wid) if wid else None,
                    user_id=int(uid) if uid else None,
                    company_id=int(cid) if cid else None,
                    task_id=str(tid) if tid else None,
                    details=details,
                    log_id=f"ch-{ts}-{wid or 'x'}",
                )
            )
        return items
    except Exception as exc:  # noqa: BLE001
        logger.debug("ClickHouse service_logs query failed: %s", exc)
        return None


async def _query_postgres(
    db: AsyncSession,
    *,
    source: str | None,
    level: str | None,
    q: str | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
    limit: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    include_service = not source or source in ("all", "worker", "api", "orchestrator", "segmentation")
    include_audit = not source or source in ("all", "audit")

    if include_service:
        stmt = select(ServiceLogEvent).order_by(ServiceLogEvent.created_at.desc()).limit(limit)
        if from_dt:
            stmt = stmt.where(ServiceLogEvent.created_at >= from_dt)
        if to_dt:
            stmt = stmt.where(ServiceLogEvent.created_at <= to_dt)
        if source == "segmentation":
            stmt = stmt.where(ServiceLogEvent.message.ilike("%segmentation%"))
        elif source and source != "all" and source != "audit":
            stmt = stmt.where(ServiceLogEvent.source == source)
        if level and level.lower() != "all":
            stmt = stmt.where(ServiceLogEvent.level == level.upper())
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    ServiceLogEvent.message.ilike(like),
                    ServiceLogEvent.worker_id.ilike(like),
                    ServiceLogEvent.task_id.ilike(like),
                )
            )
        rows = (await db.scalars(stmt)).all()
        for r in rows:
            items.append(
                _row(
                    ts=r.created_at,
                    source=r.source,
                    level=r.level,
                    message=r.message,
                    worker_id=r.worker_id,
                    user_id=r.user_id,
                    company_id=r.company_id,
                    task_id=r.task_id,
                    details=r.details,
                    log_id=f"pg-{r.id}",
                )
            )

    if include_audit:
        audit_limit = max(limit - len(items), 0)
        if audit_limit:
            astmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(audit_limit)
            if from_dt:
                astmt = astmt.where(AuditLog.created_at >= from_dt)
            if to_dt:
                astmt = astmt.where(AuditLog.created_at <= to_dt)
            if q:
                like = f"%{q}%"
                astmt = astmt.where(AuditLog.action.ilike(like))
            arows = (await db.scalars(astmt)).all()
            for r in arows:
                items.append(
                    _row(
                        ts=r.created_at,
                        source="audit",
                        level="INFO",
                        message=r.action,
                        user_id=r.user_id,
                        company_id=r.company_id,
                        details=r.details,
                        log_id=f"audit-{r.id}",
                    )
                )

    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items[:limit]


async def query_admin_logs(
    db: AsyncSession,
    *,
    source: str | None = None,
    level: str | None = None,
    q: str | None = None,
    from_param: str | None = None,
    to_param: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    limit = max(1, min(limit, 1000))
    now = datetime.now(timezone.utc)
    from_dt = _parse_dt(from_param, default=now - timedelta(hours=24))
    to_dt = _parse_dt(to_param, default=now)

    if source and source not in VALID_SOURCES:
        source = "all"
    if level and level.upper() not in VALID_LEVELS:
        level = "all"

    backend = "clickhouse"
    items = _query_clickhouse(
        source=source,
        level=level,
        q=q,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=limit,
    )

    if items is None:
        backend = "postgres"
        items = await _query_postgres(
            db,
            source=source,
            level=level,
            q=q,
            from_dt=from_dt,
            to_dt=to_dt,
            limit=limit,
        )

    if not items and settings.ENVIRONMENT == "development":
        backend = "mock"
        items = _mock_logs(limit)

    return {
        "items": items,
        "count": len(items),
        "backend": backend,
        "filters": {
            "source": source or "all",
            "level": level or "all",
            "q": q,
            "from": from_dt.isoformat() if from_dt else None,
            "to": to_dt.isoformat() if to_dt else None,
            "limit": limit,
        },
    }
