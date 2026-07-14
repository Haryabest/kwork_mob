"""Диагностика кластера хранения §11.16.4: Force Resync / Patroni / FIO."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog

logger = logging.getLogger(__name__)

FIO_DURATION_SEC = 10


async def _audit(db: AsyncSession, *, user_id: int | None, action: str, details: dict) -> None:
    db.add(
        AuditLog(
            company_id=None,
            user_id=user_id,
            action=action,
            details=details,
        )
    )
    await db.flush()


async def _call_hook(url: str, *, timeout: float = 30) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json={"triggered_at": datetime.now(timezone.utc).isoformat()})
        body: Any
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = {"raw": resp.text[:500]}
        return {"status_code": resp.status_code, "ok": 200 <= resp.status_code < 300, "body": body}


def _run_script(script: str) -> dict[str, Any]:
    path = Path(script)
    if not path.exists():
        return {"ok": False, "error": f"script not found: {script}"}
    try:
        proc = subprocess.run(
            [str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[:2000],
            "stderr": (proc.stderr or "")[:1000],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:300]}


async def force_resync_minio(db: AsyncSession, *, user_id: int | None = None) -> dict[str, Any]:
    """Кнопка Force Resync MinIO — hook URL или локальный скрипт агента."""
    url = (getattr(settings, "MINIO_FORCE_RESYNC_URL", "") or "").strip()
    script = (getattr(settings, "MINIO_FORCE_RESYNC_SCRIPT", "") or "").strip()
    result: dict[str, Any] = {"action": "force_resync_minio", "mode": None}

    if url:
        result["mode"] = "http_hook"
        result["result"] = await _call_hook(url)
    elif script:
        result["mode"] = "script"
        result["result"] = _run_script(script)
    else:
        # безопасный no-op с аудитом: агент может читать Redis/файл
        try:
            from app.core.redis import get_redis

            redis = await get_redis()
            await redis.set(
                "storage:cmd:force_resync_minio",
                datetime.now(timezone.utc).isoformat(),
                ex=3600,
            )
            result["mode"] = "redis_flag"
            result["result"] = {"ok": True, "key": "storage:cmd:force_resync_minio"}
        except Exception as exc:  # noqa: BLE001
            result["mode"] = "none"
            result["result"] = {
                "ok": False,
                "error": "Configure MINIO_FORCE_RESYNC_URL or MINIO_FORCE_RESYNC_SCRIPT",
                "detail": str(exc)[:200],
            }

    await _audit(
        db,
        user_id=user_id,
        action="storage_force_resync_minio",
        details=result,
    )
    await db.commit()
    return result


async def restart_patroni_replication(db: AsyncSession, *, user_id: int | None = None) -> dict[str, Any]:
    """Кнопка Restart Patroni Replication."""
    url = (getattr(settings, "PATRONI_RESTART_REPL_URL", "") or "").strip()
    script = (getattr(settings, "PATRONI_RESTART_REPL_SCRIPT", "") or "").strip()
    result: dict[str, Any] = {"action": "restart_patroni_replication", "mode": None}

    if url:
        result["mode"] = "http_hook"
        result["result"] = await _call_hook(url)
    elif script:
        result["mode"] = "script"
        result["result"] = _run_script(script)
    else:
        try:
            from app.core.redis import get_redis

            redis = await get_redis()
            await redis.set(
                "storage:cmd:restart_patroni_replication",
                datetime.now(timezone.utc).isoformat(),
                ex=3600,
            )
            result["mode"] = "redis_flag"
            result["result"] = {"ok": True, "key": "storage:cmd:restart_patroni_replication"}
        except Exception as exc:  # noqa: BLE001
            result["mode"] = "none"
            result["result"] = {
                "ok": False,
                "error": "Configure PATRONI_RESTART_REPL_URL or PATRONI_RESTART_REPL_SCRIPT",
                "detail": str(exc)[:200],
            }

    await _audit(
        db,
        user_id=user_id,
        action="storage_restart_patroni_replication",
        details=result,
    )
    await db.commit()
    return result


async def run_fio_disk_test(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    node: str | None = None,
) -> dict[str, Any]:
    """Кнопка «Запустить FIO-тест» — краткий 10 сек IOPS (§11.16.4)."""
    url = (getattr(settings, "FIO_TEST_URL", "") or "").strip()
    script = (getattr(settings, "FIO_TEST_SCRIPT", "") or "").strip()
    result: dict[str, Any] = {
        "action": "fio_disk_test",
        "mode": None,
        "duration_sec": FIO_DURATION_SEC,
        "node": node,
    }

    if url:
        result["mode"] = "http_hook"
        async with httpx.AsyncClient(timeout=float(FIO_DURATION_SEC) + 30) as client:
            resp = await client.post(
                url,
                json={
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                    "duration_sec": FIO_DURATION_SEC,
                    "node": node,
                },
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
                cmd = [str(path), str(FIO_DURATION_SEC)]
                if node:
                    cmd.append(node)
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=FIO_DURATION_SEC + 30,
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
            payload = {
                "at": datetime.now(timezone.utc).isoformat(),
                "duration_sec": FIO_DURATION_SEC,
                "node": node,
            }
            import json

            await redis.set(
                "storage:cmd:fio_test",
                json.dumps(payload),
                ex=3600,
            )
            result["mode"] = "redis_flag"
            result["result"] = {"ok": True, "key": "storage:cmd:fio_test", **payload}
        except Exception as exc:  # noqa: BLE001
            result["mode"] = "none"
            result["result"] = {
                "ok": False,
                "error": "Configure FIO_TEST_URL or FIO_TEST_SCRIPT",
                "detail": str(exc)[:200],
            }

    await _audit(db, user_id=user_id, action="storage_fio_disk_test", details=result)
    await db.commit()
    return result
