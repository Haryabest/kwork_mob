"""Управление GPU-воркером через Docker на хосте (web-admin → apply/restart/logs)."""

from __future__ import annotations

import json
import logging
import os
import shutil
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

# Из корневого .env orchestrator → worker/.env.worker (не в web-admin UI)
WORKER_PASS_THROUGH_ENV = (
    "QUALITY_THRESHOLD",
    "SEGMENTATION_AVG_MIN",
    "NOBG_CONFIDENCE",
    "NOBG_HARD_FAIL_MIN",
    "WATERMARK_HMAC_SECRET",
    "WORKER_SUBPROCESS_STREAM",
)


def _compose_relative() -> str:
    return (settings.WORKER_DEPLOY_COMPOSE_FILE or "worker/docker-compose.worker.yml").strip()


def _repo_root() -> Path:
    """Корень репозитория с worker/docker-compose.worker.yml."""
    rel = _compose_relative()
    candidates: list[Path] = []
    raw = (settings.WORKER_DEPLOY_ROOT or "").strip()
    if raw:
        candidates.append(Path(raw).expanduser())
    candidates.append(Path("/repo"))
    candidates.extend(Path(__file__).resolve().parents)
    seen: set[str] = set()
    for base in candidates:
        try:
            root = base.resolve()
        except OSError:
            continue
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        if (root / rel).is_file():
            return root
    if raw:
        return Path(raw).expanduser().resolve()
    return Path("/repo")


def _compose_file() -> Path:
    return _repo_root() / _compose_relative()


def _host_repo_root() -> Path:
    """Абсолютный путь к корню репо на хосте (для docker bind через socket)."""
    raw = (settings.WORKER_HOST_REPO_ROOT or os.getenv("WORKER_HOST_REPO_ROOT") or "").strip()
    if raw:
        return Path(raw).expanduser()
    deploy = (settings.WORKER_DEPLOY_ROOT or "").strip()
    if deploy and deploy != "/repo":
        return Path(deploy).expanduser()
    return _repo_root()


def _worker_dir(cfg: dict[str, Any] | None = None) -> Path:
    host_worker = _host_repo_root() / "worker"
    if not cfg:
        return host_worker
    wrp = str(cfg.get("worker_repo_path") or "").strip()
    if not wrp:
        return host_worker
    path = Path(wrp).expanduser()
    normalized = str(path).replace("\\", "/")
    if normalized in ("/repo/worker", "/app/kwork_mob/worker") or normalized.startswith(
        ("/repo/worker/", "/app/kwork_mob/worker/")
    ):
        return host_worker
    return path


def _normalize_deploy_meta(cfg: dict[str, Any]) -> dict[str, Any]:
    out = dict(cfg)
    out["worker_repo_path"] = str(_worker_dir(out))
    return out


def _env_values_match(key: str, expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    if key in ("ORCHESTRATOR_WS_URL", "ORCHESTRATOR_HTTP_URL"):
        return expected.rstrip("/") == actual.rstrip("/")
    return False


def _env_file() -> Path:
    rel = (settings.WORKER_DEPLOY_ENV_FILE or "worker/.env.worker").strip()
    return _repo_root() / rel


def _default_orchestrator_ws() -> str:
    explicit = (
        os.getenv("ORCHESTRATOR_WS_PUBLIC")
        or os.getenv("ORCHESTRATOR_WS_URL")
        or ""
    ).strip()
    if explicit:
        return explicit
    base = settings.API_BASE_URL.rstrip("/")
    if base.startswith("https://"):
        return base.replace("https://", "wss://", 1) + "/ws/worker"
    if base.startswith("http://"):
        return base.replace("http://", "ws://", 1) + "/ws/worker"
    return "ws://host.docker.internal:8000/ws/worker"


def _default_orchestrator_http() -> str:
    explicit = (os.getenv("ORCHESTRATOR_HTTP_URL") or "").strip()
    if explicit:
        return explicit
    return settings.API_BASE_URL.rstrip("/") or "http://host.docker.internal:8000"


def _worker_redis_url(url: str | None = None) -> str:
    """Redis для GPU-воркера вне compose-сети orchestrator."""
    explicit = (os.getenv("WORKER_REDIS_URL") or "").strip()
    raw = (url or explicit or settings.REDIS_URL or "").strip()
    if not raw:
        return "redis://host.docker.internal:6382/0"
    if "://redis:" in raw or raw.startswith("redis://redis"):
        return "redis://host.docker.internal:6382/0"
    if "localhost" in raw:
        return raw.replace("localhost", "host.docker.internal")
    if "127.0.0.1" in raw:
        return raw.replace("127.0.0.1", "host.docker.internal")
    return raw


def _default_redis_url() -> str:
    return _worker_redis_url()


def _normalize_worker_env(env: dict[str, str]) -> dict[str, str]:
    """Привести env воркера к адресам, доступным из GPU-контейнера вне compose-сети."""
    out = dict(env)
    ws = (out.get("ORCHESTRATOR_WS_URL") or "").strip()
    if not ws or "://orchestrator:" in ws:
        out["ORCHESTRATOR_WS_URL"] = _default_orchestrator_ws()
    http = (out.get("ORCHESTRATOR_HTTP_URL") or "").strip()
    if not http or "://orchestrator:" in http:
        out["ORCHESTRATOR_HTTP_URL"] = _default_orchestrator_http()
    minio = (out.get("MINIO_ENDPOINT") or "").strip()
    if not minio or "://minio:" in minio:
        out["MINIO_ENDPOINT"] = _default_minio_endpoint()
    return out


def _default_minio_endpoint() -> str:
    ep = settings.MINIO_ENDPOINT
    if "minio:" in ep and settings.ENVIRONMENT == "development":
        return "http://host.docker.internal:9010"
    return ep


def default_config() -> dict[str, Any]:
    root = _host_repo_root()
    worker_dir = _worker_dir()
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


def _coerce_env_map(env: Any) -> dict[str, str]:
    if not isinstance(env, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in env.items():
        out[str(k)] = "" if v is None else str(v)
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
    merged_env = {**base["env"], **_decrypt_env(_coerce_env_map(stored.get("env")))}
    if "env" in incoming:
        prev_plain = _decrypt_env(_coerce_env_map(stored.get("env")))
        for k, v in incoming["env"].items():
            if v is None:
                continue
            s = str(v)
            if k in SECRET_ENV_KEYS and (not s or s == MASK or s == UNCHANGED):
                if prev_plain.get(k):
                    merged_env[k] = prev_plain[k]
                continue
            merged_env[k] = s
    merged["env"] = _normalize_worker_env(merged_env)
    for k in ("container_name", "docker_image", "worker_repo_path", "hf_cache_host_path", "state_volume", "extra_hosts"):
        if k in incoming and incoming[k] is not None:
            merged[k] = incoming[k]
    return merged


async def get_config(*, masked: bool = True) -> dict[str, Any]:
    try:
        stored = await _redis_get()
        if not stored or not isinstance(stored, dict):
            cfg = default_config()
            cfg["env"] = _normalize_worker_env(cfg["env"])
        else:
            cfg = {**default_config(), **{k: v for k, v in stored.items() if k != "env"}}
            base_env = default_config()["env"]
            stored_env = _decrypt_env(_coerce_env_map(stored.get("env")))
            cfg["env"] = _normalize_worker_env({**base_env, **stored_env})
        out = dict(cfg)
        out["deploy_enabled"] = bool(settings.WORKER_DEPLOY_ENABLED)
        out["deploy_root"] = str(_repo_root())
        out["compose_file"] = str(_compose_file())
        out["env_file"] = str(_env_file())
        if raw := (settings.WORKER_DEPLOY_ROOT or "").strip():
            try:
                configured = Path(raw).expanduser().resolve()
            except OSError:
                configured = None
            if configured is not None and configured != _repo_root():
                out["deploy_root_hint"] = (
                    f"WORKER_DEPLOY_ROOT={raw} не содержит compose; используется {_repo_root()}"
                )
        try:
            out["docker_available"] = docker_cli_available()
            out["docker_status"] = docker_cli_status()
        except Exception as exc:  # noqa: BLE001
            logger.warning("docker_cli_status failed: %s", exc)
            out["docker_available"] = False
            out["docker_status"] = {"available": False, "reason": "docker_check_failed", "hint": str(exc)[:200]}
        if masked:
            out["env"] = _mask_env(_coerce_env_map(out.get("env")))
        out.update(_normalize_deploy_meta(out))
        out["host_repo_root"] = str(_host_repo_root())
        return out
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_config failed")
        raise HTTPException(500, f"Не удалось загрузить настройки воркера: {exc}") from exc


async def save_config(payload: dict[str, Any], *, user_id: int | None = None) -> dict[str, Any]:
    stored = await _redis_get()
    if stored:
        stored["env"] = _decrypt_env(stored.get("env") or {})
    merged = _merge_config(stored, payload)
    merged = _normalize_deploy_meta(merged)
    merged["env"] = _encrypt_env(merged["env"])
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _redis_set(merged)
    logger.info("worker deploy config saved by user_id=%s", user_id)
    return await get_config(masked=True)


def _docker_bin() -> str | None:
    for cand in (os.getenv("DOCKER_BIN", "").strip(), "docker", "/usr/bin/docker", "/usr/local/bin/docker"):
        if not cand:
            continue
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return None


def docker_cli_status() -> dict[str, object]:
    if not settings.WORKER_DEPLOY_ENABLED:
        return {
            "available": False,
            "reason": "WORKER_DEPLOY_ENABLED=0",
            "hint": "Задайте WORKER_DEPLOY_ENABLED=1 в .env и перезапустите orchestrator",
        }
    docker = _docker_bin()
    if not docker:
        return {
            "available": False,
            "reason": "docker_not_found",
            "hint": (
                "docker CLI не найден в orchestrator. "
                "Выполните: docker compose build orchestrator && docker compose up -d orchestrator. "
                "Либо смонтируйте /usr/bin/docker с хоста (см. docker-compose.yml)."
            ),
        }
    try:
        proc = subprocess.run(
            [docker, "info"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"available": False, "reason": "docker_error", "hint": str(exc)[:200]}
    if proc.returncode == 0:
        return {"available": True, "reason": "ok"}
    err = ((proc.stderr or "") + (proc.stdout or "")).strip()[-400:]
    return {
        "available": False,
        "reason": "docker_info_failed",
        "hint": err or "docker info failed — смонтируйте /var/run/docker.sock",
    }


def docker_cli_available() -> bool:
    return bool(docker_cli_status().get("available"))


def _compose_base_cmd() -> list[str]:
    """docker compose (v2 plugin) или docker-compose (v1)."""
    docker = _docker_bin() or "docker"
    proc = subprocess.run(
        [docker, "compose", "version"],
        capture_output=True,
        timeout=10,
        check=False,
    )
    if proc.returncode == 0:
        return [docker, "compose"]
    legacy = subprocess.run(
        ["docker-compose", "version"],
        capture_output=True,
        timeout=10,
        check=False,
    )
    if legacy.returncode == 0:
        return ["docker-compose"]
    return [docker, "compose"]


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
    env = _normalize_worker_env(_decrypt_env(_coerce_env_map(cfg.get("env"))))
    cfg = _normalize_deploy_meta(cfg)
    worker_dir = _worker_dir(cfg)
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
        val = str(env.get(key, "")).strip()
        if not val:
            continue
        val = val.replace("\n", "")
        if " " in val or "#" in val:
            lines.append(f'{key}="{val}"')
        else:
            lines.append(f"{key}={val}")
    for key in WORKER_PASS_THROUGH_ENV:
        val = (os.getenv(key) or "").strip()
        if val:
            lines.append(f"{key}={val}")
    return lines


def write_env_file(cfg: dict[str, Any]) -> Path:
    path = _env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(_build_env_file_lines(cfg)) + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def _stop_and_remove_container(container_name: str) -> None:
    """Снять контейнер по имени, если он создан вне текущего compose project."""
    name = (container_name or "").strip()
    if not name:
        return
    docker = _docker_bin() or "docker"
    proc = subprocess.run(
        [docker, "rm", "-f", name],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode == 0:
        logger.info("removed existing container %s", name)
    elif "No such container" not in (proc.stderr or ""):
        logger.debug("docker rm %s: %s", name, (proc.stderr or proc.stdout or "")[:300])


async def apply_config(*, user_id: int | None = None) -> dict[str, Any]:
    if not settings.WORKER_DEPLOY_ENABLED:
        raise HTTPException(503, "WORKER_DEPLOY_ENABLED=0 — управление Docker отключено")
    if not docker_cli_available():
        diag = docker_cli_status()
        raise HTTPException(
            503,
            diag.get("hint") or "Docker CLI недоступен. Смонтируйте /var/run/docker.sock в orchestrator.",
        )
    stored = await _redis_get()
    if not stored:
        stored = default_config()
    stored = _normalize_deploy_meta(stored)
    base_env = default_config()["env"]
    stored_env = _decrypt_env(_coerce_env_map(stored.get("env")))
    stored["env"] = _normalize_worker_env({**base_env, **stored_env})
    worker_dir = _worker_dir(stored)
    agent = worker_dir / "worker_agent.py"
    repo_agent = _repo_root() / "worker" / "worker_agent.py"
    if not agent.is_file() and not repo_agent.is_file():
        raise HTTPException(400, f"Не найден worker_agent.py: {agent}")
    if not agent.is_file() and not (settings.WORKER_HOST_REPO_ROOT or os.getenv("WORKER_HOST_REPO_ROOT")):
        raise HTTPException(
            400,
            "Задайте WORKER_HOST_REPO_ROOT в .env (путь к проекту на хосте, напр. /home/dom/kwork_mob). "
            "Docker на хосте не видит /repo и /app/kwork_mob.",
        )
    compose = _compose_file()
    if not compose.is_file():
        tried = [str(Path("/repo") / _compose_relative())]
        raw = (settings.WORKER_DEPLOY_ROOT or "").strip()
        if raw:
            tried.insert(0, str(Path(raw).expanduser() / _compose_relative()))
        raise HTTPException(
            404,
            f"Compose не найден: {compose}. Проверьте WORKER_DEPLOY_ROOT (для docker compose: /repo). "
            f"Искали: {', '.join(dict.fromkeys(tried))}",
        )
    env_path = write_env_file(stored)
    compose_cmd = _compose_base_cmd()
    container_name = str(stored.get("container_name") or "kwork-worker")
    _stop_and_remove_container(container_name)
    _run(
        [
            *compose_cmd,
            "-f",
            str(compose),
            "--env-file",
            str(env_path),
            "down",
            "--remove-orphans",
        ],
        timeout=180,
    )
    proc = _run(
        [
            *compose_cmd,
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
    if not ok:
        logger.error("worker deploy apply failed: %s", msg[-2000:])
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
        "message": msg[-2000:] if not ok else "Контейнер перезапущен",
        "env_file": str(env_path),
        "verify": verify,
    }


def _container_env_map(container_name: str) -> dict[str, str]:
    docker = _docker_bin() or "docker"
    proc = _run(
        [docker, "inspect", container_name, "--format", "{{json .Config.Env}}"],
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
    docker = _docker_bin() or "docker"
    proc = _run(
        [
            docker,
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
        ok = _env_values_match(key, expected, got)
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
    try:
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
    except Exception as exc:  # noqa: BLE001
        logger.exception("verify_stored_config failed")
        return {
            "ok": False,
            "message": str(exc)[:300],
            "matches": {},
            "mismatches": [],
        }


def fetch_logs(*, tail: int = 300, container_name: str | None = None) -> dict[str, Any]:
    tail = max(50, min(int(tail), 2000))
    name = (container_name or "kwork-worker").strip() or "kwork-worker"
    base: dict[str, Any] = {
        "ok": False,
        "container": name,
        "tail": tail,
        "items": [],
        "raw": "",
    }
    try:
        if not settings.WORKER_DEPLOY_ENABLED:
            base["raw"] = "WORKER_DEPLOY_ENABLED=0 — включите в .env"
            return base
        docker = _docker_bin()
        if not docker:
            base["raw"] = str(docker_cli_status().get("hint") or "docker CLI не найден")
            return base
        proc = subprocess.run(
            [docker, "logs", "--tail", str(tail), name],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0 and not text.strip():
            text = f"docker logs exit {proc.returncode}: контейнер «{name}» не найден или остановлен"
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
    except Exception as exc:  # noqa: BLE001
        logger.exception("fetch_logs failed for %s", name)
        base["raw"] = str(exc)[:500]
        return base


async def fetch_logs_async(*, tail: int = 300) -> dict[str, Any]:
    import asyncio

    stored = await _redis_get()
    name = str((stored or {}).get("container_name") or default_config()["container_name"])
    return await asyncio.to_thread(fetch_logs, tail=tail, container_name=name)
