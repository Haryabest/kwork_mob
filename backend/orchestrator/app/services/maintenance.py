"""Плановое обслуживание кластера хранения §23.7."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog, MaintenanceChecklist, ServiceLogEvent

logger = logging.getLogger(__name__)

CHECKLIST_ITEMS: list[dict[str, str]] = [
    {
        "id": "smart",
        "section": "Диски",
        "label": "Проверка S.M.A.R.T. (сектора, износ, температура)",
    },
    {
        "id": "disk_free",
        "section": "Диски",
        "label": "Свободное место ≥10% на узлах A/B",
    },
    {
        "id": "logs_cleanup",
        "section": "Логи",
        "label": "Очистка старых логов сервисов",
    },
    {
        "id": "backup_restore",
        "section": "Бэкапы",
        "label": "Тест восстановления из бэкапа PostgreSQL",
    },
    {
        "id": "minio_repl",
        "section": "Бэкапы",
        "label": "Проверка репликации MinIO / Force Resync при зависании",
    },
    {
        "id": "fio",
        "section": "Диски",
        "label": "FIO-тест IOPS (10 сек) при подозрении на деградацию SSD",
    },
]

VALID_IDS = {i["id"] for i in CHECKLIST_ITEMS}
SINGLETON_ID = 1


def normalize_checks(raw: dict | None) -> dict[str, bool]:
    out = {i["id"]: False for i in CHECKLIST_ITEMS}
    if not raw:
        return out
    for k, v in raw.items():
        if k in VALID_IDS:
            out[k] = bool(v)
    return out


async def get_checklist(db: AsyncSession) -> dict[str, Any]:
    row = await db.get(MaintenanceChecklist, SINGLETON_ID)
    checks = normalize_checks(row.checks if row else {})
    done = sum(1 for v in checks.values() if v)
    return {
        "items": CHECKLIST_ITEMS,
        "checks": checks,
        "done": done,
        "total": len(CHECKLIST_ITEMS),
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
        "updated_by_user_id": row.updated_by_user_id if row else None,
    }


async def put_checklist(
    db: AsyncSession,
    *,
    checks: dict[str, bool],
    user_id: int | None = None,
) -> dict[str, Any]:
    normalized = normalize_checks(checks)
    row = await db.get(MaintenanceChecklist, SINGLETON_ID)
    if not row:
        row = MaintenanceChecklist(id=SINGLETON_ID, checks=normalized, updated_by_user_id=user_id)
        db.add(row)
    else:
        row.checks = normalized
        row.updated_by_user_id = user_id
        row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return await get_checklist(db)


async def cleanup_service_logs(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    older_than_days: int | None = None,
) -> dict[str, Any]:
    """Очистка PG service_log_events старше N дней."""
    days = older_than_days
    if days is None:
        days = int(getattr(settings, "SERVICE_LOG_RETENTION_DAYS", 14) or 14)
    days = max(1, min(days, 365))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    before = int(await db.scalar(select(func.count()).select_from(ServiceLogEvent)) or 0)
    result = await db.execute(delete(ServiceLogEvent).where(ServiceLogEvent.created_at < cutoff))
    deleted = int(result.rowcount or 0)
    db.add(
        AuditLog(
            user_id=user_id,
            action="maintenance_logs_cleanup",
            details={"deleted": deleted, "older_than_days": days, "cutoff": cutoff.isoformat()},
        )
    )
    await db.commit()
    return {
        "ok": True,
        "deleted": deleted,
        "before": before,
        "older_than_days": days,
        "cutoff": cutoff.isoformat(),
    }


async def backup_restore_test(db: AsyncSession, *, user_id: int | None = None) -> dict[str, Any]:
    """Тест восстановления из бэкапа — hook URL / script / Redis flag."""
    import json
    import subprocess
    from pathlib import Path

    import httpx

    url = (getattr(settings, "BACKUP_RESTORE_TEST_URL", "") or "").strip()
    script = (getattr(settings, "BACKUP_RESTORE_TEST_SCRIPT", "") or "").strip()
    result: dict[str, Any] = {"action": "backup_restore_test", "mode": None}

    if url:
        result["mode"] = "http_hook"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                json={"triggered_at": datetime.now(timezone.utc).isoformat()},
            )
            try:
                body = resp.json()
            except Exception:  # noqa: BLE001
                body = {"raw": resp.text[:500]}
            result["result"] = {
                "status_code": resp.status_code,
                "ok": 200 <= resp.status_code < 300,
                "body": body,
            }
    elif script:
        result["mode"] = "script"
        path = Path(script)
        if not path.exists():
            result["result"] = {"ok": False, "error": f"script not found: {script}"}
        else:
            try:
                proc = subprocess.run(
                    [str(path)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=False,
                )
                result["result"] = {
                    "ok": proc.returncode == 0,
                    "returncode": proc.returncode,
                    "stdout": (proc.stdout or "")[:2000],
                    "stderr": (proc.stderr or "")[:1000],
                }
            except Exception as exc:  # noqa: BLE001
                result["result"] = {"ok": False, "error": str(exc)[:300]}
    else:
        try:
            from app.core.redis import get_redis

            redis = await get_redis()
            payload = {"at": datetime.now(timezone.utc).isoformat()}
            await redis.set("storage:cmd:backup_restore_test", json.dumps(payload), ex=3600)
            result["mode"] = "redis_flag"
            result["result"] = {"ok": True, "key": "storage:cmd:backup_restore_test", **payload}
        except Exception as exc:  # noqa: BLE001
            result["mode"] = "none"
            result["result"] = {
                "ok": False,
                "error": "Configure BACKUP_RESTORE_TEST_URL or BACKUP_RESTORE_TEST_SCRIPT",
                "detail": str(exc)[:200],
            }

    db.add(
        AuditLog(
            user_id=user_id,
            action="maintenance_backup_restore_test",
            details=result,
        )
    )
    await db.commit()
    return result
