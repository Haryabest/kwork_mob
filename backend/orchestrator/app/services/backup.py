"""Резервное копирование PostgreSQL → MinIO (§9.3–9.4)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)


def _pg_env() -> tuple[dict[str, str], dict[str, str]]:
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(db_url)
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    conn = {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "postgres",
        "database": (parsed.path or "/kwork").lstrip("/"),
    }
    return env, conn


def gpg_encrypt_file(path: Path) -> Path:
    """GPG-шифрование бэкапа §9.4."""
    recipient = (settings.BACKUP_GPG_RECIPIENT or "").strip()
    if not recipient or not settings.BACKUP_GPG_ENABLED:
        return path
    if not shutil.which("gpg"):
        logger.warning("gpg not found — skip encryption")
        return path
    out = path.with_suffix(path.suffix + ".gpg")
    proc = subprocess.run(
        ["gpg", "--batch", "--yes", "--encrypt", "-r", recipient, "-o", str(out), str(path)],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode(errors="replace")[-500:]
        raise RuntimeError(f"gpg encrypt failed: {err}")
    return out


def run_pg_dump_to_minio() -> dict:
    """pg_dump | gzip [+ GPG] → s3://backups/postgres/YYYY/MM/DD/dump-HHMM.sql.gz"""
    env, conn = _pg_env()
    stamp = datetime.now(timezone.utc).strftime("%Y/%m/%d/dump-%H%M%S.sql.gz")
    key = f"postgres/{stamp}"

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "dump.sql.gz"
        dump = subprocess.run(
            [
                "pg_dump",
                "-h",
                conn["host"],
                "-p",
                conn["port"],
                "-U",
                conn["user"],
                "-d",
                conn["database"],
                "--no-owner",
                "--format=plain",
            ],
            capture_output=True,
            env=env,
            check=False,
        )
        if dump.returncode != 0:
            err = (dump.stderr or b"").decode(errors="replace")[-500:]
            raise RuntimeError(f"pg_dump failed: {err}")

        import gzip

        with gzip.open(out, "wb") as gz:
            gz.write(dump.stdout)

        upload_path = gpg_encrypt_file(out)
        if upload_path != out:
            key = key + ".gpg"

        from app.services.minio import minio_service

        minio_service.upload_file(settings.MINIO_BUCKET_BACKUPS, key, str(upload_path))
        size = upload_path.stat().st_size
        logger.info("PG backup uploaded s3://%s/%s (%s bytes)", settings.MINIO_BUCKET_BACKUPS, key, size)
        return {
            "key": key,
            "bytes": size,
            "bucket": settings.MINIO_BUCKET_BACKUPS,
            "encrypted": upload_path != out,
            "method": "pg_dump",
        }


def run_walg_backup_push() -> dict:
    """WAL-G full backup §9.4 (требует wal-g + PGDATA на узле)."""
    if not settings.WALG_ENABLED:
        return {"skipped": True, "reason": "WALG_ENABLED=false"}

    walg_bin = (settings.WALG_BIN or "wal-g").strip()
    if not shutil.which(walg_bin):
        return {"skipped": True, "reason": f"{walg_bin} not in PATH"}

    env = os.environ.copy()
    pgdata = (settings.WALG_PGDATA or "").strip()
    if pgdata:
        env["PGDATA"] = pgdata
    prefix = (settings.WALG_S3_PREFIX or "").strip()
    if prefix:
        env["WALG_S3_PREFIX"] = prefix
    env.setdefault("AWS_ACCESS_KEY_ID", settings.MINIO_ACCESS_KEY)
    env.setdefault("AWS_SECRET_ACCESS_KEY", settings.MINIO_SECRET_KEY)
    env.setdefault("AWS_ENDPOINT", settings.MINIO_ENDPOINT)
    env.setdefault("AWS_S3_FORCE_PATH_STYLE", "true")

    proc = subprocess.run([walg_bin, "backup-push", pgdata or env.get("PGDATA", "")], capture_output=True, env=env, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode(errors="replace")[-800:]
        raise RuntimeError(f"wal-g backup-push failed: {err}")
    out = (proc.stdout or b"").decode(errors="replace").strip()
    logger.info("WAL-G backup-push ok: %s", out[:200])
    return {"ok": True, "method": "wal-g", "output": out[:500]}


def run_backup_suite() -> dict:
    """Полный набор: pg_dump (+ GPG) и опционально WAL-G."""
    results: dict = {"pg_dump": None, "wal_g": None}
    results["pg_dump"] = run_pg_dump_to_minio()
    try:
        results["wal_g"] = run_walg_backup_push()
    except Exception as exc:  # noqa: BLE001
        logger.warning("WAL-G backup skipped/failed: %s", exc)
        results["wal_g"] = {"error": str(exc)}
    return results
