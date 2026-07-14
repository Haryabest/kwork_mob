"""Deploy bundles для воркера / storage / оркестратора (§15.3 / §20 / §11.3.3)."""

from __future__ import annotations

import os
import secrets
from typing import Any

from app.core.config import settings
from app.services.cloud_client import worker_bootstrap_script


def _ws_public() -> str:
    explicit = os.getenv("ORCHESTRATOR_WS_PUBLIC", "").strip()
    if explicit:
        return explicit
    base = settings.API_BASE_URL.rstrip("/")
    if base.startswith("https://"):
        return base.replace("https://", "wss://", 1) + "/ws/worker"
    if base.startswith("http://"):
        return base.replace("http://", "ws://", 1) + "/ws/worker"
    return "wss://api.example.com/ws/worker"


def _worker_token() -> str:
    return os.getenv("WORKER_TOKEN", "").strip() or "change-me-worker-token"


def worker_bundle(*, worker_id: str | None = None) -> dict[str, Any]:
    """JSON для развёртывания GPU-воркера (Docker + Tailscale, §15.3)."""
    wid = worker_id or os.getenv("WORKER_ID", "worker-1")
    ws = _ws_public()
    token = _worker_token()
    image = os.getenv("WORKER_DOCKER_IMAGE", "kwork-worker:trellis2")
    env = {
        "WORKER_ID": wid,
        "ORCHESTRATOR_WS_URL": ws,
        "ORCHESTRATOR_WS_FALLBACK_URL": ws,
        "WORKER_TOKEN": token,
        "WORKER_PIPELINE_MODE": os.getenv("WORKER_PIPELINE_MODE", "trellis"),
        "TRELLIS_ALLOW_STUB_FALLBACK": os.getenv("TRELLIS_ALLOW_STUB_FALLBACK", "0"),
        "TRELLIS_VERSION": "2",
        "TRELLIS2_PIPELINE_TYPE": os.getenv("TRELLIS2_PIPELINE_TYPE", "512"),
        "TRELLIS2_LOW_VRAM": os.getenv("TRELLIS2_LOW_VRAM", "1"),
        "ATTN_BACKEND": os.getenv("ATTN_BACKEND", "xformers"),
        "MINIO_ENDPOINT": os.getenv("MINIO_ENDPOINT", settings.MINIO_ENDPOINT),
        "MINIO_ACCESS_KEY": os.getenv("MINIO_ACCESS_KEY", settings.MINIO_ACCESS_KEY),
        "MINIO_SECRET_KEY": os.getenv("MINIO_SECRET_KEY", settings.MINIO_SECRET_KEY),
        "REDIS_URL": os.getenv("REDIS_URL", settings.REDIS_URL),
        "TAILSCALE_AUTH_KEY": os.getenv("TAILSCALE_AUTH_KEY", ""),
        "WATERMARK_HMAC_SECRET": os.getenv("WATERMARK_HMAC_SECRET", ""),
        "CLOUD_PROVIDER": os.getenv("CLOUD_PROVIDER", "intelion"),
        "WORKER_GIT_REPO": os.getenv("WORKER_GIT_REPO", ""),
        "WORKER_GIT_BRANCH": os.getenv("WORKER_GIT_BRANCH", "main"),
    }
    bootstrap = worker_bootstrap_script(
        worker_id=wid,
        orchestrator_ws=ws,
        worker_token=token,
        image_env={k: v for k, v in env.items() if v},
    )
    return {
        "role": "worker",
        "version": "1",
        "description": "GPU worker TRELLIS.2 — Docker + Tailscale (§5 / §15.3)",
        "docker_image": image,
        "compose_file": "worker/docker-compose.worker.yml",
        "env": env,
        "bootstrap_sh": bootstrap,
        "run_example": (
            f"docker run -d --gpus all --restart unless-stopped --name kwork-worker "
            f"-e ORCHESTRATOR_WS_URL={ws} -e WORKER_TOKEN=<secret> -e WORKER_ID={wid} "
            f"{image}"
        ),
        "notes": [
            "TRELLIS_ALLOW_STUB_FALLBACK=0 на prod/cloud (§6)",
            "Tailscale IP MinIO/Redis — из панели Storage",
            "Облако: bootstrap_sh через cloud create meta",
        ],
    }


def storage_bundle(*, node: str = "primary") -> dict[str, Any]:
    """JSON для узла хранения (MinIO+PG+Redis+ClickHouse, §20)."""
    role = node.lower()
    if role not in ("primary", "replica", "1", "2"):
        role = "primary"
    node_label = "primary" if role in ("primary", "1") else "replica"
    return {
        "role": "storage",
        "node": node_label,
        "version": "1",
        "description": "Storage HA node — docker-compose.ha.yml (§20 / §22)",
        "compose_file": "docker-compose.ha.yml",
        "env": {
            "POSTGRES_USER": settings.POSTGRES_USER,
            "POSTGRES_PASSWORD": "<set-in-panel>",
            "POSTGRES_DB": settings.POSTGRES_DB,
            "POSTGRES_REPLICATOR_PASSWORD": "<set-in-panel>",
            "MINIO_ROOT_USER": settings.MINIO_ACCESS_KEY,
            "MINIO_ROOT_PASSWORD": "<set-in-panel>",
            "TAILSCALE_AUTH_KEY": os.getenv("TAILSCALE_AUTH_KEY", ""),
            "MINIO_HA_JSON": os.getenv("MINIO_HA_JSON", ""),
            "LOKI_URL": os.getenv("LOKI_URL", settings.LOKI_URL or ""),
            "CLICKHOUSE_HOST": settings.CLICKHOUSE_HOST,
            "CLICKHOUSE_DB": settings.CLICKHOUSE_DB,
            "STORAGE_NODE_ID": f"storage-{node_label}",
        },
        "services": ["postgres-primary", "postgres-replica", "redis-master", "redis-replica", "minio-primary", "minio-replica", "clickhouse"],
        "notes": [
            "Primary: node=primary; Replica: node=replica",
            "Patroni cutover — docs/deployment/HA.md",
            "Tailscale на обоих узлах обязателен (§4.3.1)",
        ],
    }


def orchestrator_bundle() -> dict[str, Any]:
    """JSON для VPS оркестратора (§4 / §6)."""
    return {
        "role": "orchestrator",
        "version": "1",
        "description": "VPS orchestrator + Celery + Nginx (§4)",
        "compose_file": "docker-compose.yml",
        "env": {
            "ENVIRONMENT": "production",
            "API_BASE_URL": settings.API_BASE_URL,
            "ORCHESTRATOR_WS_PUBLIC": _ws_public(),
            "SECRET_KEY": "<rotate>",
            "JWT_SECRET": "<rotate>",
            "POSTGRES_HOST": "<storage-tailscale-ip>",
            "REDIS_URL": "redis://<storage-tailscale-ip>:6379/0",
            "MINIO_ENDPOINT": "http://<storage-tailscale-ip>:9000",
            "CLICKHOUSE_HOST": "<storage-tailscale-ip>",
            "CLOUD_INTELION_TOKEN": "<token>",
            "CLOUD_IMMERS_TOKEN": "<token>",
            "YOOKASSA_SHOP_ID": "<set>",
            "YOOKASSA_SECRET_KEY": "<set>",
            "PD_ENCRYPTION_KEY": "<set-or-vault>",
            "TRELLIS_ALLOW_STUB_FALLBACK": "0",
            "MARKETPLACE_UPLOAD_ENABLED": os.getenv("MARKETPLACE_UPLOAD_ENABLED", "false"),
        },
        "notes": [
            "Alembic upgrade head перед запуском",
            "celery-worker + celery-beat обязательны",
            "ADMIN_VPN_REQUIRED=true на prod",
        ],
    }


def cloud_env_template() -> dict[str, Any]:
    """Шаблон env для блока B (Intelion/Immers, §11.3.3)."""
    return {
        "role": "cloud_gpu",
        "version": "1",
        "env": {
            "CLOUD_INTELION_TOKEN": "<token>",
            "CLOUD_IMMERS_TOKEN": "<token>",
            "CLOUD_API_MOCK": "0",
            "INTELION_FLAVOR_ID": os.getenv("INTELION_FLAVOR_ID", ""),
            "INTELION_OS_ID": os.getenv("INTELION_OS_ID", ""),
            "IMMERS_FLAVOR_ID": os.getenv("IMMERS_FLAVOR_ID", ""),
            "IMMERS_OS_ID": os.getenv("IMMERS_OS_ID", ""),
            "ORCHESTRATOR_WS_PUBLIC": _ws_public(),
            "WORKER_DOCKER_IMAGE": os.getenv("WORKER_DOCKER_IMAGE", "kwork-worker:trellis2"),
            "TRELLIS_ALLOW_STUB_FALLBACK": "0",
            "CLOUD_DAILY_BUDGET_RUB": os.getenv("CLOUD_DAILY_BUDGET_RUB", "0"),
            "CLOUD_BURN_ALERT_RUB_PER_HOUR": os.getenv("CLOUD_BURN_ALERT_RUB_PER_HOUR", "500"),
        },
        "cli_smoke": [
            "python worker/cloud/provision.py --action providers",
            "python worker/cloud/provision.py --action flavors --provider intelion",
            "python worker/cloud/provision.py --action create --provider intelion --gpu rtx4090",
        ],
    }


def build_bundle(role: str, **kwargs: Any) -> dict[str, Any]:
    r = role.lower().strip()
    if r == "worker":
        return worker_bundle(**kwargs)
    if r in ("storage", "storage-primary", "storage-replica"):
        node = "replica" if "replica" in r else kwargs.get("node", "primary")
        return storage_bundle(node=node)
    if r == "orchestrator":
        return orchestrator_bundle()
    if r in ("cloud", "cloud_gpu"):
        return cloud_env_template()
    if r == "all":
        return {
            "bundles": {
                "orchestrator": orchestrator_bundle(),
                "storage_primary": storage_bundle(node="primary"),
                "storage_replica": storage_bundle(node="replica"),
                "worker": worker_bundle(),
                "cloud_gpu": cloud_env_template(),
            },
            "generated_at": secrets.token_hex(4),
        }
    raise ValueError(f"unknown role: {role}")
