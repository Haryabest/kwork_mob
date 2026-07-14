"""REST GPU-облака Intelion + Immers (§14.7).

Intelion: https://intelion.cloud/api/v2/  Token auth, cloud-servers/flavors/os-images
Immers:  https://immers.cloud/api/       Token/Bearer, cabinet API + OpenStack (env paths)

Адреса: .claude/Адреса Облачных Воркеров.txt
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PROVIDERS: dict[str, dict[str, str]] = {
    "intelion": {
        "label": "Intelion Cloud",
        "site": "https://intelion.cloud/",
        "api": "https://intelion.cloud/api/v2/",
        "support": "@CareIntelionCloud_bot",
        "stop_mode": "shelve",
        "auth": "token",
        "api_style": "intelion_v2",
    },
    "immers": {
        "label": "Immers Cloud",
        "site": "https://immers.cloud/",
        "api": "https://immers.cloud/api/v2/",
        "support": "https://immers.cloud/",
        "stop_mode": "shelve",
        "auth": "bearer",
        "api_style": "intelion_v2",
    },
}

_INTELION_STATUS = {
    2: "running",
    1: "starting",
    3: "preparing",
    -1: "stopped",
    -3: "terminated",
    -2: "requested",
}


@dataclass
class CloudInstance:
    id: str
    provider: str
    status: str
    gpu: str
    public_ip: str | None = None
    tailscale_ip: str | None = None
    login: str | None = None
    bootstrap_script: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class CloudProviderError(RuntimeError):
    pass


def cloud_token(provider: str, override: str | None = None) -> str:
    provider = provider.lower()
    if override:
        return override.strip()
    env_key = f"CLOUD_{provider.upper()}_TOKEN"
    return (os.getenv(env_key) or os.getenv("CLOUD_API_TOKEN") or "").strip()


def cloud_api_base(provider: str, override: str | None = None) -> str:
    provider = provider.lower()
    raw = (
        override
        or os.getenv(f"CLOUD_{provider.upper()}_API_BASE")
        or os.getenv("CLOUD_API_BASE")
        or PROVIDERS[provider]["api"]
    ).rstrip("/")
    if provider == "intelion" or PROVIDERS[provider].get("api_style") == "intelion_v2":
        if raw.endswith("/api/v2"):
            return raw + "/"
        if raw.endswith("/api"):
            return raw + "/v2/"
        if "/api/" not in raw:
            return raw + "/api/v2/"
    return raw + "/"


def cloud_env_int(provider: str, name: str) -> int | None:
    """INTELION_FLAVOR_ID / IMMERS_FLAVOR_ID / CLOUD_INTELION_FLAVOR_ID."""
    for key in (
        f"{provider.upper()}_{name}",
        f"CLOUD_{provider.upper()}_{name}",
    ):
        if val := os.getenv(key, "").strip():
            return int(val)
    return None


def worker_bootstrap_script(
    *,
    worker_id: str,
    orchestrator_ws: str,
    worker_token: str,
    image_env: dict[str, str],
) -> str:
    provider = image_env.get("CLOUD_PROVIDER", "intelion")
    env_lines = "\n".join(f'export {k}="{v}"' for k, v in image_env.items() if v)
    repo = image_env.get("WORKER_GIT_REPO", "https://github.com/your-org/kwork_mob.git")
    branch = image_env.get("WORKER_GIT_BRANCH", "main")
    return f"""#!/bin/bash
set -eux
{env_lines}
export WORKER_ID="{worker_id}"
export ORCHESTRATOR_WS_URL="{orchestrator_ws}"
export WORKER_TOKEN="{worker_token}"
export WORKER_PIPELINE_MODE=trellis
export CLOUD_PROVIDER={provider}

if [ -n "${{TAILSCALE_AUTH_KEY:-}}" ]; then
  curl -fsSL https://tailscale.com/install.sh | sh || true
  tailscale up --authkey="$TAILSCALE_AUTH_KEY" --hostname="{worker_id}" || true
fi

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
if ! docker info 2>/dev/null | grep -qi nvidia; then
  distribution=$(. /etc/os-release; echo "$ID$VERSION_ID")
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L "https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list" \\
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \\
    | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  apt-get update && apt-get install -y nvidia-container-toolkit
  nvidia-ctk runtime configure --runtime=docker && systemctl restart docker
fi

WORKDIR="${{WORKER_BUILD_DIR:-/opt/kwork_mob}}"
if [ ! -d "$WORKDIR/.git" ]; then
  git clone --depth 1 -b {branch} {repo} "$WORKDIR"
fi
cd "$WORKDIR/worker"
docker build --build-arg INSTALL_TRELLIS=1 --build-arg DOWNLOAD_WEIGHTS=1 \\
  --build-arg TRELLIS_VERSION=2 --build-arg INSTALL_FLASH_ATTN=0 \\
  -t kwork-worker:trellis2 .
docker rm -f kwork-worker 2>/dev/null || true
docker run -d --gpus all --restart unless-stopped --name kwork-worker \\
  -e ORCHESTRATOR_WS_URL -e WORKER_TOKEN -e WORKER_ID -e WORKER_PIPELINE_MODE \\
  -e MINIO_ENDPOINT -e MINIO_ACCESS_KEY -e MINIO_SECRET_KEY -e CLOUD_PROVIDER \\
  -e TRELLIS_VERSION=2 -e TRELLIS2_PIPELINE_TYPE=512 -e TRELLIS2_LOW_VRAM=1 \\
  -e ATTN_BACKEND=xformers -e ORCHESTRATOR_WS_FALLBACK_URL \\
  kwork-worker:trellis2
echo "[bootstrap] worker started: $WORKER_ID provider=$CLOUD_PROVIDER"
"""


cloud_user_data = worker_bootstrap_script


class _CabinetV2Backend(ABC):
    """Intelion API v2 и совместимый cabinet API (Immers)."""

    provider: str

    def __init__(self, *, token: str, base_url: str, meta: dict[str, str]):
        self.provider = meta.get("_name", "unknown")
        self.meta = meta
        self.token = token
        self.base = base_url
        self.mock = os.getenv("CLOUD_API_MOCK", "0").lower() in ("1", "true", "yes")
        self._timeout = float(os.getenv("CLOUD_API_TIMEOUT", "120"))
        self._retries = int(os.getenv("CLOUD_API_RETRIES", "5"))

    def _env_prefix(self) -> str:
        return self.provider.upper()

    def _paths(self) -> dict[str, str]:
        p = self._env_prefix()
        return {
            "create": os.getenv(f"{p}_PATH_CREATE", os.getenv("CLOUD_PATH_CREATE", "cloud-servers/")),
            "get": os.getenv(f"{p}_PATH_GET", os.getenv("CLOUD_PATH_GET", "cloud-servers/{id}/")),
            "delete": os.getenv(f"{p}_PATH_DELETE", os.getenv("CLOUD_PATH_DELETE", "cloud-servers/{id}/actions/")),
            "shelve": os.getenv(f"{p}_PATH_SHELVE", os.getenv("CLOUD_PATH_SHELVE", "cloud-servers/{id}/actions/")),
            "start": os.getenv(f"{p}_PATH_START", os.getenv("CLOUD_PATH_START", "cloud-servers/{id}/actions/")),
            "flavors": os.getenv(f"{p}_PATH_FLAVORS", os.getenv("CLOUD_PATH_FLAVORS", "flavors/")),
            "os_images": os.getenv(f"{p}_PATH_OS_IMAGES", os.getenv("CLOUD_PATH_OS_IMAGES", "os-images/")),
            "password": os.getenv(f"{p}_PATH_PASSWORD", os.getenv("CLOUD_PATH_PASSWORD", "cloud-servers/{id}/password/")),
        }

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json", "Content-Type": "application/json"}
        if not self.token:
            return h
        if self.meta.get("auth") == "token":
            h["Authorization"] = f"Token {self.token}"
        else:
            h["Authorization"] = f"Bearer {self.token}"
            h["X-API-Key"] = self.token
        return h

    def _path(self, key: str, **fmt: str) -> str:
        return self._paths()[key].format(**fmt).lstrip("/")

    def _request(self, method: str, path: str, json_body: dict | None = None, params: dict | None = None) -> Any:
        if self.mock:
            return self._mock(method, path, json_body)
        if not self.token:
            raise CloudProviderError(f"CLOUD_{self._env_prefix()}_TOKEN (или CLOUD_API_TOKEN) не задан")
        url = self.base + path
        last_err: Exception | None = None
        delay = 1.0
        for attempt in range(1, self._retries + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.request(method, url, headers=self._headers(), json=json_body, params=params)
                if resp.status_code >= 500:
                    raise CloudProviderError(f"[{self.provider}] HTTP {resp.status_code}: {resp.text[:300]}")
                if resp.status_code >= 400:
                    raise CloudProviderError(f"[{self.provider}] HTTP {resp.status_code}: {resp.text[:500]}")
                if not resp.content:
                    return {}
                return resp.json()
            except CloudProviderError:
                raise
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning("[%s] API %s %s attempt %s: %s", self.provider, method, path, attempt, exc)
                if attempt >= self._retries:
                    break
                time.sleep(delay)
                delay = min(delay * 2, 30)
        raise CloudProviderError(str(last_err))

    def _list_paginated(self, path: str, *, params: dict | None = None) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
            p = dict(params or {})
            p["page"] = page
            data = self._request("GET", path, params=p)
            if isinstance(data, list):
                items.extend(data)
                break
            chunk = data.get("results") or data.get("items") or data.get("data") or data.get("flavors") or []
            if isinstance(chunk, list):
                items.extend(chunk)
            if not data.get("next"):
                break
            page += 1
            if page > 50:
                break
        return items

    def _mock(self, method: str, path: str, json_body: dict | None) -> dict[str, Any]:
        tag = self.provider
        if "flavor" in path:
            base = 12000 if tag == "intelion" else 11000
            return {
                "results": [
                    {
                        "id": 1,
                        "name": f"RTX 4090 ({tag})",
                        "gpu": {"name": "RTX 4090"},
                        "flavor_hourly_price_rub_cents": base,
                        "max_available": 2,
                    },
                    {
                        "id": 2,
                        "name": f"A100 40GB ({tag})",
                        "gpu": {"name": "A100"},
                        "flavor_hourly_price_rub_cents": 28000,
                        "max_available": 1,
                    },
                ]
            }
        if "os-image" in path:
            return {"results": [{"id": 1, "name": "Ubuntu 22.04 CUDA", "os_type": "lin"}]}
        if method == "POST" and "actions" in path:
            status = -1 if (json_body or {}).get("status") == -1 else 2
            return {"id": 1, "status": status, "ip_to_connect": "203.0.113.20"}
        if method == "POST":
            return {
                "id": f"mock-{tag}-{uuid.uuid4().hex[:8]}",
                "status": -2,
                "ip_to_connect": "203.0.113.20",
                "login": "root",
            }
        if method == "GET":
            iid = path.rstrip("/").split("/")[-1]
            return {"id": iid, "status": 2, "ip_to_connect": "203.0.113.20", "login": "root"}
        return {}

    def list_flavors(self) -> list[dict[str, Any]]:
        raw = self._list_paginated(self._path("flavors"))
        out = []
        for f in raw:
            gpu = f.get("gpu") or {}
            gpu_name = gpu.get("name") if isinstance(gpu, dict) else str(gpu or "")
            hourly = (
                f.get("flavor_hourly_price_rub_cents")
                or f.get("hourly_price_rub_cents")
                or f.get("price_per_hour_cents")
                or 0
            )
            out.append(
                {
                    "provider": self.provider,
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "gpu": gpu_name,
                    "vram_gb": gpu.get("vram_gb") if isinstance(gpu, dict) else f.get("vram_gb"),
                    "rub_per_hour": int(hourly) // 100 if hourly else f.get("rub_per_hour"),
                    "max_available": f.get("max_available"),
                    "raw": f,
                }
            )
        return out

    def list_os_images(self, *, flavor_id: int | None = None) -> list[dict[str, Any]]:
        params = {"flavor_id": flavor_id} if flavor_id else None
        return self._list_paginated(self._path("os_images"), params=params)

    def get_password(self, instance_id: str) -> str:
        try:
            data = self._request("GET", self._path("password", id=instance_id))
            if isinstance(data, dict):
                return str(data.get("password") or data.get("credentials") or "")
            return str(data)
        except CloudProviderError:
            return ""

    def _resolve_flavor_id(self, gpu: str) -> int:
        if fid := cloud_env_int(self.provider, "FLAVOR_ID"):
            return fid
        slug = re.sub(r"[^a-z0-9]", "", gpu.lower())
        for f in self.list_flavors():
            name = re.sub(r"[^a-z0-9]", "", str(f.get("name", "")).lower())
            gname = re.sub(r"[^a-z0-9]", "", str(f.get("gpu", "")).lower())
            if slug and (slug in name or slug in gname):
                return int(f["id"])
        raise CloudProviderError(
            f"[{self.provider}] Flavor для gpu={gpu!r} не найден. "
            f"Задайте {self._env_prefix()}_FLAVOR_ID или --flavor-id"
        )

    def _resolve_os_id(self, flavor_id: int) -> int:
        if oid := cloud_env_int(self.provider, "OS_ID"):
            return oid
        images = self.list_os_images(flavor_id=flavor_id)
        if not images:
            raise CloudProviderError(
                f"[{self.provider}] Нет OS images для flavor_id={flavor_id}. "
                f"Задайте {self._env_prefix()}_OS_ID"
            )
        for img in images:
            name = str(img.get("name", "")).lower()
            os_type = str(img.get("os_type") or img.get("type") or "").lower()
            if "ubuntu" in name or os_type in ("lin", "linux"):
                return int(img["id"])
        return int(images[0]["id"])

    def create_instance(
        self,
        *,
        gpu: str,
        image: str,
        worker_id: str,
        vcpus: int = 8,
        ram_gb: int = 32,
        user_data: str | None = None,
        flavor_id: int | None = None,
        os_id: int | None = None,
        ssd_gb: int | None = None,
    ) -> CloudInstance:
        fid = flavor_id or self._resolve_flavor_id(gpu)
        oid = os_id or self._resolve_os_id(fid)
        disk = ssd_gb or cloud_env_int(self.provider, "SSD_GB") or int(
            os.getenv("CLOUD_SSD_GB", "100")
        )
        price_plan = cloud_env_int(self.provider, "PRICE_PLAN")
        if price_plan is None:
            price_plan = int(os.getenv("CLOUD_PRICE_PLAN", "0"))
        body = {
            "name": worker_id,
            "flavor_id": fid,
            "ssd_count": max(disk, 30),
            "os_id": oid,
            "price_plan": price_plan,
        }
        data = self._request("POST", self._path("create"), body)
        inst = self._parse_instance(data)
        if inst.status not in ("running", "starting"):
            try:
                inst = self.start_instance(str(inst.id))
            except CloudProviderError as exc:
                logger.warning("[%s] auto-start %s: %s", self.provider, inst.id, exc)
        inst.bootstrap_script = user_data
        return inst

    def get_instance(self, instance_id: str) -> CloudInstance:
        data = self._request("GET", self._path("get", id=instance_id))
        return self._parse_instance(data)

    def start_instance(self, instance_id: str) -> CloudInstance:
        data = self._request("POST", self._path("start", id=instance_id), {"status": 2})
        return self._parse_instance(data)

    def stop_instance(self, instance_id: str, *, shelve: bool | None = None) -> dict[str, Any]:
        use_shelve = shelve if shelve is not None else (self.meta.get("stop_mode") == "shelve")
        status = -1 if use_shelve else -3
        return self._request("POST", self._path("shelve", id=instance_id), {"status": status})

    def _parse_instance(self, data: dict[str, Any]) -> CloudInstance:
        nested = data.get("instance") if isinstance(data.get("instance"), dict) else data
        raw_status = nested.get("status") or nested.get("state") or "unknown"
        if isinstance(raw_status, int):
            status = _INTELION_STATUS.get(raw_status, str(raw_status))
        else:
            status = str(raw_status)
        gpu_obj = nested.get("gpu")
        gpu_name = nested.get("flavor") or nested.get("gpu")
        if isinstance(gpu_obj, dict):
            gpu_name = gpu_obj.get("name") or gpu_name
        ip = (
            nested.get("ip_to_connect")
            or nested.get("public_ip")
            or nested.get("ip")
            or nested.get("address")
        )
        if not ip and nested.get("white_ips"):
            ips = nested["white_ips"]
            if ips and isinstance(ips[0], dict):
                ip = ips[0].get("address_v4")
        return CloudInstance(
            id=str(nested.get("id") or nested.get("uuid") or nested.get("instance_id") or ""),
            provider=self.provider,
            status=status,
            gpu=str(gpu_name or ""),
            public_ip=ip,
            tailscale_ip=nested.get("tailscale_ip") or nested.get("ts_ip"),
            login=nested.get("login") or "root",
            raw=data if isinstance(data, dict) else {"data": data},
        )


class IntelionBackend(_CabinetV2Backend):
    pass


class ImmersBackend(_CabinetV2Backend):
    pass


def _make_backend(provider: str, *, token: str | None, base_url: str | None) -> _CabinetV2Backend:
    provider = provider.lower()
    meta = {**PROVIDERS[provider], "_name": provider}
    tok = cloud_token(provider, token)
    base = cloud_api_base(provider, base_url)
    cls = IntelionBackend if provider == "intelion" else ImmersBackend
    backend = cls(token=tok, base_url=base, meta=meta)
    backend.provider = provider
    return backend


class CloudProviderClient:
    """Фасад: intelion | immers."""

    def __init__(self, provider: str, *, token: str | None = None, base_url: str | None = None):
        provider = provider.lower()
        if provider not in PROVIDERS:
            raise CloudProviderError(f"unknown provider: {provider}. Доступны: {', '.join(PROVIDERS)}")
        self.provider = provider
        self.meta = PROVIDERS[provider]
        self._backend = _make_backend(provider, token=token, base_url=base_url)

    @property
    def base(self) -> str:
        return self._backend.base

    @property
    def token(self) -> str:
        return self._backend.token

    @property
    def mock(self) -> bool:
        return self._backend.mock

    def list_flavors(self) -> list[dict[str, Any]]:
        return self._backend.list_flavors()

    def list_os_images(self, *, flavor_id: int | None = None) -> list[dict[str, Any]]:
        return self._backend.list_os_images(flavor_id=flavor_id)

    def get_password(self, instance_id: str) -> str:
        return self._backend.get_password(instance_id)

    def create_instance(self, **kwargs: Any) -> CloudInstance:
        return self._backend.create_instance(**kwargs)

    def get_instance(self, instance_id: str) -> CloudInstance:
        return self._backend.get_instance(instance_id)

    def start_instance(self, instance_id: str) -> CloudInstance:
        return self._backend.start_instance(instance_id)

    def stop_instance(self, instance_id: str, *, shelve: bool | None = None) -> dict[str, Any]:
        return self._backend.stop_instance(instance_id, shelve=shelve)


def list_providers() -> list[dict[str, str]]:
    return [
        {
            "id": pid,
            "label": meta["label"],
            "site": meta["site"],
            "api": meta["api"],
            "support": meta.get("support", ""),
            "stop_mode": meta["stop_mode"],
        }
        for pid, meta in PROVIDERS.items()
    ]
