"""HA cutover preflight §22.3 — проверки перед переключением на Patroni VIP."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.services.ha_readiness import ha_readiness
from app.services.mesh_hosts import mesh_recommendations, mesh_status
from app.services.minio import minio_service
from app.services.witness_status import witness_status


def _http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with httpx.Client(timeout=timeout) as client:
            return client.get(url).status_code < 500
    except Exception:  # noqa: BLE001
        return False


def cutover_preflight() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    patroni_url = (settings.PATRONI_REST_URL or "").strip()
    patroni_ok = bool(patroni_url) and _http_ok(f"{patroni_url.rstrip('/')}/primary")
    checks.append(
        {
            "id": "patroni_primary",
            "pass": patroni_ok,
            "detail": patroni_url or "PATRONI_REST_URL not set",
        }
    )

    haproxy_host = (settings.HAPROXY_PG_HOST or settings.POSTGRES_HOST or "").strip()
    haproxy_ok = bool(haproxy_host)
    checks.append(
        {
            "id": "haproxy_pg_host",
            "pass": haproxy_ok,
            "detail": haproxy_host or "POSTGRES_HOST empty",
        }
    )

    sentinel_ok = bool((settings.REDIS_SENTINELS or "").strip())
    checks.append(
        {
            "id": "redis_sentinel",
            "pass": sentinel_ok,
            "detail": settings.REDIS_SENTINELS or "REDIS_SENTINELS not set",
        }
    )

    smart = minio_service.smart()
    minio_ok = bool(smart.get("ok"))
    checks.append(
        {
            "id": "minio_online",
            "pass": minio_ok,
            "detail": smart.get("note") or ("ok" if minio_ok else "minio unreachable"),
        }
    )

    replica_ok = bool((settings.MINIO_REPLICA_ENDPOINT or "").strip())
    checks.append(
        {
            "id": "minio_replica_endpoint",
            "pass": replica_ok,
            "detail": settings.MINIO_REPLICA_ENDPOINT or "MINIO_REPLICA_ENDPOINT not set",
        }
    )

    mesh = mesh_status()
    checks.append(
        {
            "id": "tailscale_mesh",
            "pass": mesh.get("ok", False) or not mesh.get("configured"),
            "detail": f"online {mesh.get('online')}/{mesh.get('total')}",
        }
    )

    witness = witness_status()
    checks.append(
        {
            "id": "witness_quorum",
            "pass": witness.get("ok") or not witness.get("url"),
            "detail": witness.get("error") or witness.get("state") or "ok",
        }
    )

    ha = ha_readiness()
    passed = sum(1 for c in checks if c["pass"])
    return {
        "ready": passed >= 5,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "ha_readiness": ha,
        "recommendations": mesh_recommendations(),
        "runbook": "docs/deployment/HA.md#runbook-cutover-postgresql-на-patroni-vip-223",
    }
