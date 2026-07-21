"""pg_partman maintenance §9.3.2."""

from __future__ import annotations

import logging
import os
import subprocess
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)


def run_partman_maintenance() -> dict:
    """SELECT partman.run_maintenance() через psql (если PARTMAN_ENABLED)."""
    if not settings.PARTMAN_ENABLED:
        return {"skipped": True, "reason": "PARTMAN_ENABLED=false"}

    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(db_url)
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = [
        "psql",
        "-h",
        parsed.hostname or "localhost",
        "-p",
        str(parsed.port or 5432),
        "-U",
        parsed.username or "postgres",
        "-d",
        (parsed.path or "/kwork").lstrip("/"),
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        "SELECT partman.run_maintenance();",
    ]
    proc = subprocess.run(cmd, capture_output=True, env=env, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode(errors="replace")[-800:]
        raise RuntimeError(f"partman maintenance failed: {err}")
    out = (proc.stdout or b"").decode(errors="replace").strip()
    logger.info("pg_partman maintenance ok: %s", out[:200])
    return {"ok": True, "output": out[:500]}
