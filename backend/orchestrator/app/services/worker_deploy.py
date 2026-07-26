"""Управление GPU-воркером через Docker на хосте (web-admin → apply/restart/logs)."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.core.crypto import decrypt_field, encrypt_field

logger = logging.getLogger(__name__)

REDIS_KEY = "trellis:worker:deploy:v1"
SECRET_ENV_KEYS = frozenset({"WORKER_TOKEN", "HF_TOKEN", "MINIO_SECRET_KEY", "MINIO_ACCESS_KEY"})
MASK = "••••••••"
UNCHANGED = "__UNCHANGED__"

CONFIG_ENV_KEYS = (
    "WORKER_ID",
    "WORKER_TOKEN",
    "WORKER_PIPELINE_MODE",
    "TRELLIS_VERSION",
    "TRELLIS2_PIPELINE_TYPE",
    "TRELLIS2_TEXTURE_SIZE",
    "TRELLIS2_DECIMATION",
    "TRELLIS2_LOW_VRAM",
    "WORKER_TRELLIS_INPROCESS",
    "WORKER_WARMUP_TRELLIS",
    "ATTN_BACKEND",
    "PYTORCH_CUDA_ALLOC_CONF",
    "NOBG_ENGINE",
    "NOBG_VIEW00_ONLY",
    "HF_TOKEN",
    "ORCHESTRATOR_WS_URL",
    "ORCHESTRATOR_HTTP_URL",
    "REDIS_URL",
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
)


def _repo_root() -> Path:
    raw = (settings.WORKER_DEPLOY_ROOT or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    # backend/orchestrator → repo root
    return Path(__file__).resolve().parents[4]


def _compose_file() -> Path:
    rel = (settings.WORKER_DEPLOY_COMPOSE_FILE or "worker/docker-compose.worker.yml").strip()
    return _repo_root() / rel


def _env_file() -> Path:
    rel = (settings.WORKER_DEPLOY_ENV_FILE or "worker/.env.worker").strip()
    return _repo_root() / rel


def _default_orchestrator_ws() -> str:
    explicit = (os.getenv("ORCHESTRATOR_WS_PUBLIC") or "").strip()
    if explicit:
        return explicit
    base = settings.API_BASE_URL.rstrip("/")
    if base.startswith("https://"):
        return base.replace("https://", "wss://", 1) + "/ws/worker"
    if base.startswith("http://"):
        return base.replace("http://", "ws://", 1) + "/ws/worker"
    return "ws://host.docker.internal:8000/ws/worker"


def _default_orchestrator_http() -> str:
    return settings.API_BASE_URL.rstrip("/") or "http://host.docker.internal:8000"


def _default_redis_url() -> str:
    url = settings.REDIS_URL
    if "redis:" in url and settings.ENVIRONMENT == "development":
        return "redis://host.docker.internal:6382/0"
    return url


def _default_minio_endpoint() -> str:
    ep = settings.MINIO_ENDPOINT
    if "minio:" in ep and settings.ENVIRONMENT == "development":
        return "http://host.docker.internal:9010"
    return ep


def default_config() -> dict[str, Any]:
    root = _repo_root()
    worker_dir = root / "worker"
    return {
        "container_name": "kwork-worker",
        "docker_image": os.getenv("WORKER_DOCKER_IMAGE", "kwork-worker:trellis2-runtime"),
        "worker_repo_path": str(worker_dir),
        "hf_cache_host_path": str(Path.home() / "hf_cache"),
        "state_volume": "kwork_worker_state",
        "extra_hosts": "host.docker.internal:host-gateway",
        "env": {
            "WORKER_ID": "client-gpu-01",
            "WORKER_TOKEN": settings.WORKER_TOKEN or "worker-dev-token",
            "WORKER_PIPELINE_MODE": "trellis",
            "TRELLIS_VERSION": "2",
            "TRELLIS2_PIPELINE_TYPE": "1024",
            "TRELLIS2_TEXTURE_SIZE": "1024",
            "TRELLIS2_DECIMATION": "150000",
            "TRELLIS2_LOW_VRAM": "1",
            "WORKER_TRELLIS_INPROCESS": "1",
            "WORKER_WARMUP_TRELLIS": "1",
            "ATTN_BACKEND": "xformers",
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "NOBG_ENGINE": "rmbg2",
            "NOBG_VIEW00_ONLY": "1",
            "HF_TOKEN": "",
            "ORCHESTRATOR_WS_URL": _default_orchestrator_ws(),
            "ORCHESTRATOR_HTTP_URL": _default_orchestrator_http(),
            "REDIS_URL": _default_redis_url(),
            "MINIO_ENDPOINT": _default_minio_endpoint(),
            "MINIO_ACCESS_KEY": settings.MINIO_ACCESS_KEY,
            "MINIO_SECRET_KEY": settings.MINIO_SECRET_KEY,
        },
        "updated_at": None,
        "applied_at": None,
        "last_apply_ok": None,
        "last_apply_message": "",
    }


async def _redis_get() -> dict[str, Any]:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        raw = await redis.get(REDIS_KEY)
        if not raw:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode()
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("worker deploy redis get: %s", exc)
        return {}


async def _redis_set(data: dict[str, Any]) -> None:
    from app.core.redis import get_redis

    redis = await get_redis()
    await redis.set(REDIS_KEY, json.dumps(data, ensure_ascii=False))


def _encrypt_env(env: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in env.items():
        val = (v or "").strip()
        if k in SECRET_ENV_KEYS and val:
            enc = encrypt_field(val)
            out[k] = enc if enc else val
        else:
            out[k] = val
    return out


def _decrypt_env(env: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in env.items():
        if k in SECRET_ENV_KEYS and v:
            try:
                out[k] = decrypt_field(v) or ""
            except Exception:  # noqa: BLE001
                out[k] = v
        else:
            out[k] = v
    return out


def _mask_env(env: dict[str, str]) -> dict[str, str]:
    out = dict(env)
    for k in SECRET_ENV_KEYS:
        if out.get(k):
            out[k] = MASK
    return out


def _merge_config(stored: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    base = default_config()
    merged = {**base, **{k: v for k, v in stored.items() if k != "env"}}
    merged_env = {**base["env"], **stored.get("env", {})}
    if "env" in incoming:
        prev_plain = _decrypt_env(stored.get("env") or {})
        for k, v in incoming["env"].items():
            if v is None:
                continue
            s = str(v)
            if k in SECRET_ENV_KEYS and (not s or s == MASK or s == UNCHANGED):
                if prev_plain.get(k):
                    merged_env[k] = prev_plain[k]
                continue
            merged_env[k] = s
    merged["env"] = merged_env
    for k in ("container_name", "docker_image", "worker_repo_path", "hf_cache_host_path", "state_volume", "extra_hosts"):
        if k in incoming and incoming[k] is not None:
            merged[k] = incoming[k]
    return merged


async def get_config(*, masked: bool = True) -> dict[str, Any]:
    stored = await _redis_get()
    if not stored:
        cfg = default_config()
    else:
        cfg = stored
        cfg["env"] = _decrypt_env(cfg.get("env") or {})
    out = dict(cfg)
    out["deploy_enabled"] = bool(settings.WORKER_DEPLOY_ENABLED)
    out["deploy_root"] = str(_repo_root())
    out["compose_file"] = str(_compose_file())
    out["env_file"] = str(_env_file())
    out["docker_available"] = docker_cli_available()
    if masked:
        out["env"] = _mask_env(out.get("env") or {})
    return out


async def save_config(payload: dict[str, Any], *, user_id: int | None = None) -> dict[str, Any]:
    stored = await _redis_get()
    if stored:
        stored["env"] = _decrypt_env(stored.get("env") or {})
    merged = _merge_config(stored, payload)
    merged["env"] = _encrypt_env(merged["env"])
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _redis_set(merged)
    logger.info("worker deploy config saved by user_id=%s", user_id)
    return await get_config(masked=True)


def docker_cli_available() -> bool:
    if not settings.WORKER_DEPLOY_ENABLED:
        return False
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=15,
            check=False,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _run(cmd: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    logger.info("worker deploy: %s", " ".join(cmd))
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(_repo_root()),
        check=False,
    )


def _build_env_file_lines(cfg: dict[str, Any]) -> list[str]:
    env = _decrypt_env(cfg.get("env") or {})
    worker_dir = Path(str(cfg.get("worker_repo_path") or _repo_root() / "worker")).expanduser()
    hf_cache = str(Path(str(cfg.get("hf_cache_host_path") or "~/hf_cache")).expanduser())
    lines = [
        f"WORKER_CONTAINER_NAME={cfg.get('container_name', 'kwork-worker')}",
        f"WORKER_DOCKER_IMAGE={cfg.get('docker_image', 'kwork-worker:trellis2-runtime')}",
        f"WORKER_VOLUME_STATE={cfg.get('state_volume', 'kwork_worker_state')}",
        f"WORKER_VOLUME_HF_CACHE={hf_cache}",
        f"WORKER_BIND_ENTRYPOINT={worker_dir / 'entrypoint.sh'}",
        f"WORKER_BIND_SCRIPTS={worker_dir / 'scripts'}",
        f"WORKER_BIND_AGENT={worker_dir / 'worker_agent.py'}",
        f"WORKER_EXTRA_HOSTS={cfg.get('extra_hosts', 'host.docker.internal:host-gateway')}",
    ]
    for key in CONFIG_ENV_KEYS:
        if key in env and env[key] != "":
            val = str(env[key]).replace("\n", "")
            if " " in val or "#" in val:
                lines.append(f'{key}="{val}"')
            else:
                lines.append(f"{key}={val}")
    return lines


def write_env_file(cfg: dict[str, Any]) -> Path:
    path = _env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(_build_env_file_lines(cfg)) + "\n"
    path.write_text(content, encoding="utf-8")
    return path


async def apply_config(*, user_id: int | None = None) -> dict[str, Any]:
    if not settings.WORKER_DEPLOY_ENABLED:
        raise HTTPException(503, "WORKER_DEPLOY_ENABLED=0 — управление Docker отключено")
    if not docker_cli_available():
        raise HTTPException(
            503,
            "Docker CLI недоступен. Смонтируйте /var/run/docker.sock в orchestrator и установите docker CLI.",
        )
    stored = await _redis_get()
    if not stored:
        stored = default_config()
    stored["env"] = _decrypt_env(stored.get("env") or {})
    compose = _compose_file()
    if not compose.is_file():
        raise HTTPException(404, f"Compose не найден: {compose}")
    env_path = write_env_file(stored)
    proc = _run(
        [
            "docker",
            "compose",
            "-f",
            str(compose),
            "--env-file",
            str(env_path),
            "up",
            "-d",
            "--force-recreate",
            "worker",
        ],
        timeout=900,
    )
    ok = proc.returncode == 0
    msg = (proc.stdout or "") + (proc.stderr or "")
    stored_enc = dict(stored)
    stored_enc["env"] = _encrypt_env(stored["env"])
    stored_enc["applied_at"] = datetime.now(timezone.utc).isoformat()
    stored_enc["last_apply_ok"] = ok
    stored_enc["last_apply_message"] = msg[-4000:]
    await _redis_set(stored_enc)
    logger.info("worker deploy apply ok=%s user_id=%s", ok, user_id)
    verify = verify_applied_config(stored)
    return {
        "ok": ok,
        "message": msg[-2000:],
        "env_file": str(env_path),
        "verify": verify,
    }


def _container_env_map(container_name: str) -> dict[str, str]:
    proc = _run(
        ["docker", "inspect", container_name, "--format", "{{json .Config.Env}}"],
        timeout=30,
    )
    if proc.returncode != 0:
        raise HTTPException(404, f"Контейнер «{container_name}» не найден: {proc.stderr[:300]}")
    try:
        arr = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(500, "Не удалось разобрать env контейнера") from exc
    out: dict[str, str] = {}
    for item in arr:
        if "=" in item:
            k, _, v = item.partition("=")
            out[k] = v
    return out


def _container_status(container_name: str) -> dict[str, Any]:
    proc = _run(
        [
            "docker",
            "inspect",
            container_name,
            "--format",
            "{{.State.Status}}|{{.State.Running}}|{{.Config.Image}}|{{.State.StartedAt}}",
        ],
        timeout=30,
    )
    if proc.returncode != 0:
        return {"running": False, "status": "missing", "image": None, "started_at": None}
    parts = (proc.stdout or "").strip().split("|", 3)
    while len(parts) < 4:
        parts.append("")
    return {
        "status": parts[0] or "unknown",
        "running": parts[1].lower() == "true",
        "image": parts[2] or None,
        "started_at": parts[3] or None,
    }


def verify_applied_config(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    if cfg is None:
        cfg = default_config()
    env = _decrypt_env(cfg.get("env") or {})
    name = str(cfg.get("container_name") or "kwork-worker")
    status = _container_status(name)
    if not status["running"]:
        return {
            "ok": False,
            "container": name,
            "status": status,
            "matches": {},
            "mismatches": [],
            "message": "Контейнер не запущен",
        }
    try:
        actual = _container_env_map(name)
    except HTTPException as exc:
        return {
            "ok": False,
            "container": name,
            "status": status,
            "matches": {},
            "mismatches": [],
            "message": exc.detail,
        }
    matches: dict[str, bool] = {}
    mismatches: list[dict[str, str]] = []
    for key in CONFIG_ENV_KEYS:
        expected = str(env.get(key, ""))
        if not expected and key in SECRET_ENV_KEYS:
            continue
        got = actual.get(key, "")
        ok = expected == got
        matches[key] = ok
        if not ok:
            mismatches.append(
                {
                    "key": key,
                    "expected": MASK if key in SECRET_ENV_KEYS else expected,
                    "actual": MASK if key in SECRET_ENV_KEYS else got,
                }
            )
    image_expected = str(cfg.get("docker_image") or "")
    image_actual = status.get("image") or ""
    image_ok = not image_expected or image_expected in image_actual
    all_ok = image_ok and not mismatches
    return {
        "ok": all_ok,
        "container": name,
        "status": status,
        "matches": matches,
        "mismatches": mismatches,
        "image_match": image_ok,
        "message": "Настройки применены" if all_ok else "Есть расхождения с контейнером",
    }


async def verify_stored_config() -> dict[str, Any]:
    stored = await _redis_get()
    if not stored:
        stored = default_config()
    else:
        stored = dict(stored)
        stored["env"] = _decrypt_env(stored.get("env") or {})
    result = verify_applied_config(stored)
    result["saved_at"] = stored.get("updated_at")
    result["applied_at"] = stored.get("applied_at")
    result["last_apply_ok"] = stored.get("last_apply_ok")
    return result


def fetch_logs(*, tail: int = 300) -> dict[str, Any]:
    if not settings.WORKER_DEPLOY_ENABLED:
        raise HTTPException(503, "WORKER_DEPLOY_ENABLED=0")
    if not docker_cli_available():
        raise HTTPException(503, "Docker CLI недоступен")
    tail = max(50, min(int(tail), 2000))
    name = "kwork-worker"
    proc = _run(["docker", "logs", "--tail", str(tail), name], timeout=60)
    text = (proc.stdout or "") + (proc.stderr or "")
    lines = text.splitlines()
    now = datetime.now(timezone.utc).isoformat()
    items = [
        {"timestamp": now, "message": line, "level": "INFO", "source": "docker"}
        for line in lines
    ]
    return {
        "ok": proc.returncode == 0 or bool(lines),
        "container": name,
        "tail": tail,
        "items": items,
        "raw": text[-12000:],
    }
