"""MinIO bucket replication prod path §14.4 / §22.2.4."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.minio import minio_service

_BUCKETS = (
    settings.MINIO_BUCKET_PHOTOS,
    settings.MINIO_BUCKET_MODELS,
    settings.MINIO_BUCKET_BACKUPS,
    "checkpoints",
)


def replication_status() -> dict[str, Any]:
    """Статус репликации: HA JSON sidecar + health MinIO."""
    smart = minio_service.smart()
    ha = smart.get("cluster_ha") or {}
    repl = ha.get("minio_replication") or []
    failed = [
        r
        for r in repl
        if str(r.get("status") or "").lower() in ("failed", "fail", "error", "paused")
    ]
    prod_hooks = bool(
        (getattr(settings, "MINIO_FORCE_RESYNC_URL", "") or "").strip()
        or (getattr(settings, "MINIO_FORCE_RESYNC_SCRIPT", "") or "").strip()
    )
    replica = (getattr(settings, "MINIO_REPLICA_ENDPOINT", "") or "").strip()
    return {
        "ok": smart.get("ok", False) and not bool(failed),
        "buckets": list(_BUCKETS),
        "replication": repl,
        "failed_count": len(failed),
        "alert_replication_failed": smart.get("alert_replication_failed", False),
        "source": ha.get("source"),
        "prod_path": prod_hooks or bool((getattr(settings, "MINIO_HA_JSON", "") or "").strip()),
        "replica_endpoint": replica or None,
        "read_failover": bool(replica),
        "setup_script": "infra/ha/minio/setup-replication.sh",
        "compose_service": "minio-replicate",
    }


def replication_status_for_bucket(bucket: str) -> dict[str, Any]:
    """Статус репликации для одного bucket (в т.ч. dedicated)."""
    base = replication_status()
    repl = [r for r in base.get("replication", []) if r.get("bucket") == bucket]
    return {
        "bucket": bucket,
        "replication": repl,
        "read_failover": base.get("read_failover"),
        "replica_endpoint": base.get("replica_endpoint"),
    }


async def apply_prod_replication(db, *, user_id: int | None = None) -> dict[str, Any]:
    """Prod apply: делегирует force_resync / hook агенту узла."""
    from app.services import storage_ops as so

    status_before = replication_status()
    result = await so.force_resync_minio(db, user_id=user_id)
    return {
        "action": "apply_minio_replication",
        "status_before": status_before,
        **result,
    }
