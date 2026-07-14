"""Централизованные логи для staff-панели (§11.5)."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.core.vpn import require_vpn
from app.services.log_query import query_admin_logs


def _vpn_guard(request: Request) -> None:
    require_vpn(request)


router = APIRouter(dependencies=[Depends(_vpn_guard)])


@router.get("/logs")
async def admin_logs(
    request: Request,
    source: str | None = Query(None, description="worker|api|audit|orchestrator|all"),
    level: str | None = Query(None, description="DEBUG|INFO|WARNING|ERROR|all"),
    q: str | None = Query(None, description="Поиск по тексту / worker_id / task_id"),
    from_param: str | None = Query(None, alias="from"),
    to: str | None = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=1000),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """GET /admin/logs — фильтры по источнику, уровню, периоду (§11.5)."""
    return await query_admin_logs(
        db,
        source=source,
        level=level,
        q=q,
        from_param=from_param,
        to_param=to,
        limit=limit,
    )


@router.get("/logs/export")
async def admin_logs_export(
    source: str | None = Query(None),
    level: str | None = Query(None),
    q: str | None = Query(None),
    from_param: str | None = Query(None, alias="from"),
    to: str | None = Query(None, alias="to"),
    limit: int = Query(5000, ge=1, le=10000),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """CSV-выгрузка логов за период (§11.5)."""
    data = await query_admin_logs(
        db,
        source=source,
        level=level,
        q=q,
        from_param=from_param,
        to_param=to,
        limit=limit,
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["timestamp", "level", "source", "message", "worker_id", "task_id", "user_id", "company_id"]
    )
    for row in data["items"]:
        w.writerow(
            [
                row.get("timestamp"),
                row.get("level"),
                row.get("source"),
                row.get("message"),
                row.get("worker_id") or "",
                row.get("task_id") or "",
                row.get("user_id") or "",
                row.get("company_id") or "",
            ]
        )
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="admin_logs.csv"'},
    )
