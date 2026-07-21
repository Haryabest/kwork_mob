"""Prod HA readiness checklist §22.1."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.minio import minio_service


def ha_readiness() -> dict[str, Any]:
    smart = minio_service.smart()
    ha = smart.get("cluster_ha") or {}
    pg = ha.get("postgres") or {}
    pg_role = str(pg.get("role") or "").lower()
    pg_ok = pg_role in ("", "primary", "master", "leader", "replica")
    sentinel_ok = bool((settings.REDIS_SENTINELS or "").strip())
    ha_json_ok = bool((settings.MINIO_HA_JSON or "").strip())
    replica_ok = bool((getattr(settings, "MINIO_REPLICA_ENDPOINT", "") or "").strip())
    checks: dict[str, Any] = {
        "minio_online": bool(smart.get("ok")),
        "minio_replication_ok": not bool(smart.get("alert_replication_failed")),
        "minio_read_failover": replica_ok,
        "minio_vip_configured": bool((getattr(settings, "MINIO_VIP", "") or "").strip()),
        "postgres_role_ok": pg_ok,
        "redis_sentinel_configured": sentinel_ok,
        "ha_json_sidecar": ha_json_ok,
        "clickhouse_host": bool((settings.CLICKHOUSE_HOST or "").strip()),
        "disk_not_critical": not bool(smart.get("alert_disk_critical")),
        "witness_configured": bool((settings.WITNESS_URL or "").strip()),
        "victoria_metrics_configured": bool((settings.VICTORIA_METRICS_URL or "").strip()),
        "debezium_configured": bool((settings.DEBEZIUM_CONNECT_URL or "").strip()),
        "tailscale_mesh_configured": bool(
            (settings.MESH_POSTGRES_HOSTS or settings.MESH_REDIS_HOSTS or settings.MESH_MINIO_HOSTS or "").strip()
        ),
        "cloudflare_waf": bool(settings.CLOUDFLARE_WAF_ENABLED),
    }
    prod_score = sum(1 for v in checks.values() if v)
    return {
        "ready": prod_score >= 6 and checks["minio_online"],
        "checks": checks,
        "score": f"{prod_score}/{len(checks)}",
        "compose": "docker-compose.ha.yml",
        "profiles": ["patroni"],
        "docs": "docs/deployment/HA.md",
        "postgres": pg,
        "nodes": ha.get("nodes") or [],
    }
