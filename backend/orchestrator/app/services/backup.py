"""Резервное копирование PostgreSQL → MinIO (§9 / §13)."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)


def run_pg_dump_to_minio() -> dict:
    """pg_dump | gzip → s3://backups/postgres/YYYY/MM/DD/dump-HHMM.sql.gz"""
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(db_url)
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    stamp = datetime.now(timezone.utc).strftime("%Y/%m/%d/dump-%H%M%S.sql.gz")
    key = f"postgres/{stamp}"

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "dump.sql.gz"
        dump = subprocess.run(
            [
                "pg_dump",
                "-h",
                parsed.hostname or "localhost",
                "-p",
                str(parsed.port or 5432),
                "-U",
                parsed.username or "postgres",
                "-d",
                (parsed.path or "/kwork").lstrip("/"),
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

        from app.services.minio import minio_service

        minio_service.upload_file(settings.MINIO_BUCKET_BACKUPS, key, str(out))
        size = out.stat().st_size
        logger.info("PG backup uploaded s3://%s/%s (%s bytes)", settings.MINIO_BUCKET_BACKUPS, key, size)
        return {"key": key, "bytes": size, "bucket": settings.MINIO_BUCKET_BACKUPS}
