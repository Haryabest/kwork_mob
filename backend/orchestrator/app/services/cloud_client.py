"""REST-клиенты Intelion Cloud / Immers Cloud (§14.7).

Пути API настраиваются env (провайдеры эволюционируют):
  CLOUD_API_BASE, CLOUD_API_TOKEN
  CLOUD_PATH_CREATE=/v1/instances
  CLOUD_PATH_GET=/v1/instances/{id}
  CLOUD_PATH_DELETE=/v1/instances/{id}
  CLOUD_PATH_SHELVE=/v1/instances/{id}/shelve
  CLOUD_PATH_FLAVORS=/v1/flavors
  CLOUD_API_MOCK=0|1  — локальный симулятор без реального API
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PROVIDERS = {
    "intelion": {
        "site": "https://intelion.cloud/",
        "api": "https://intelion.cloud/api/",
        "stop_mode": "terminate",
    },
    "immers": {
        "site": "https://immers.cloud/",
        "api": "https://immers.cloud/api/",
        "stop_mode": "shelve",
    },
}


@dataclass
class CloudInstance:
    id: str
    provider: str
    status: str
    gpu: str
    public_ip: str | None = None
    tailscale_ip: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class CloudProviderError(RuntimeError):
    pass


class CloudProviderClient:
    def __init__(self, provider: str, *, token: str | None = None, base_url: str | None = None):
        provider = provider.lower()
        if provider not in PROVIDERS:
            raise CloudProviderError(f"unknown provider: {provider}")
        self.provider = provider
        self.meta = PROVIDERS[provider]
        self.token = (token or os.getenv("CLOUD_API_TOKEN") or "").strip()
        self.base = (base_url or os.getenv("CLOUD_API_BASE") or self.meta["api"]).rstrip("/") + "/"
        self.mock = os.getenv("CLOUD_API_MOCK", "0").lower() in ("1", "true", "yes")
        self._timeout = float(os.getenv("CLOUD_API_TIMEOUT", "60"))
        self._retries = int(os.getenv("CLOUD_API_RETRIES", "5"))

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
            h["X-API-Key"] = self.token
        return h

    def _path(self, key: str, **fmt: str) -> str:
        defaults = {
            "create": os.getenv("CLOUD_PATH_CREATE", "v1/instances"),
            "get": os.getenv("CLOUD_PATH_GET", "v1/instances/{id}"),
            "delete": os.getenv("CLOUD_PATH_DELETE", "v1/instances/{id}"),
            "shelve": os.getenv("CLOUD_PATH_SHELVE", "v1/instances/{id}/shelve"),
            "flavors": os.getenv("CLOUD_PATH_FLAVORS", "v1/flavors"),
            "start": os.getenv("CLOUD_PATH_START", "v1/instances/{id}/start"),
        }
        return defaults[key].format(**fmt).lstrip("/")

    def _request(self, method: str, path: str, json_body: dict | None = None) -> dict[str, Any]:
        if self.mock:
            return self._mock(method, path, json_body)
        if not self.token:
            raise CloudProviderError("CLOUD_API_TOKEN не задан")
        url = self.base + path
        last_err: Exception | None = None
        delay = 1.0
        for attempt in range(1, self._retries + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.request(method, url, headers=self._headers(), json=json_body)
                if resp.status_code >= 500:
                    raise CloudProviderError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                if resp.status_code >= 400:
                    raise CloudProviderError(f"HTTP {resp.status_code}: {resp.text[:500]}")
                if not resp.content:
                    return {}
                data = resp.json()
                return data if isinstance(data, dict) else {"data": data}
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning("cloud API %s %s attempt %s: %s", method, path, attempt, exc)
                if attempt >= self._retries:
                    break
                time.sleep(delay)
                delay = min(delay * 2, 30)
        raise CloudProviderError(str(last_err))

    def _mock(self, method: str, path: str, json_body: dict | None) -> dict[str, Any]:
        """Локальный симулятор для CI / без ключа провайдера."""
        if path.endswith("flavors") or path.endswith("v1/flavors"):
            return {
                "items": [
                    {"id": "rtx4090", "name": "RTX 4090", "vram_gb": 24, "rub_per_hour": 120},
                    {"id": "a100", "name": "A100 40GB", "vram_gb": 40, "rub_per_hour": 280},
                    {"id": "l40s", "name": "L40S", "vram_gb": 48, "rub_per_hour": 220},
                ]
            }
        if method == "POST" and "shelve" in path:
            return {"id": path.split("/")[-2], "status": "shelved"}
        if method == "POST" and path.endswith("start"):
            iid = path.split("/")[-2]
            return {"id": iid, "status": "running", "tailscale_ip": "100.64.0.50"}
        if method == "POST":
            iid = f"mock-{uuid.uuid4().hex[:10]}"
            return {
                "id": iid,
                "status": "running",
                "gpu": (json_body or {}).get("gpu") or "rtx4090",
                "public_ip": "203.0.113.10",
                "tailscale_ip": "100.64.1.10",
            }
        if method == "GET":
            iid = path.rstrip("/").split("/")[-1]
            return {
                "id": iid,
                "status": "running",
                "gpu": "rtx4090",
                "public_ip": "203.0.113.10",
                "tailscale_ip": "100.64.1.10",
            }
        if method == "DELETE":
            return {"ok": True, "status": "terminated"}
        return {}

    def list_flavors(self) -> list[dict[str, Any]]:
        data = self._request("GET", self._path("flavors"))
        items = data.get("items") or data.get("flavors") or data.get("data") or []
        return list(items)

    def create_instance(
        self,
        *,
        gpu: str,
        image: str,
        worker_id: str,
        vcpus: int = 8,
        ram_gb: int = 32,
        user_data: str | None = None,
    ) -> CloudInstance:
        body = {
            "gpu": gpu,
            "flavor": gpu,
            "image": image,
            "name": worker_id,
            "vcpus": vcpus,
            "ram_gb": ram_gb,
            "user_data": user_data or "",
            "tags": {"role": "kwork-worker", "worker_id": worker_id},
        }
        data = self._request("POST", self._path("create"), body)
        return self._parse_instance(data)

    def get_instance(self, instance_id: str) -> CloudInstance:
        data = self._request("GET", self._path("get", id=instance_id))
        return self._parse_instance(data)

    def start_instance(self, instance_id: str) -> CloudInstance:
        data = self._request("POST", self._path("start", id=instance_id), {})
        if not data.get("id"):
            data = self.get_instance(instance_id).raw
        return self._parse_instance(data)

    def stop_instance(self, instance_id: str, *, shelve: bool | None = None) -> dict[str, Any]:
        use_shelve = shelve if shelve is not None else (self.meta["stop_mode"] == "shelve")
        if use_shelve:
            try:
                return self._request("POST", self._path("shelve", id=instance_id), {})
            except CloudProviderError:
                logger.info("shelve unavailable, falling back to terminate")
        return self._request("DELETE", self._path("delete", id=instance_id))

    def _parse_instance(self, data: dict[str, Any]) -> CloudInstance:
        nested = data.get("instance") if isinstance(data.get("instance"), dict) else data
        return CloudInstance(
            id=str(nested.get("id") or nested.get("uuid") or nested.get("instance_id") or ""),
            provider=self.provider,
            status=str(nested.get("status") or nested.get("state") or "unknown"),
            gpu=str(nested.get("gpu") or nested.get("flavor") or ""),
            public_ip=nested.get("public_ip") or nested.get("ip") or nested.get("address"),
            tailscale_ip=nested.get("tailscale_ip") or nested.get("ts_ip"),
            raw=data,
        )


def cloud_user_data(*, worker_id: str, orchestrator_ws: str, worker_token: str, image_env: dict[str, str]) -> str:
    """cloud-init: Tailscale + docker run worker."""
    env_lines = "\n".join(f"export {k}={v}" for k, v in image_env.items())
    return f"""#!/bin/bash
set -eux
{env_lines}
export WORKER_ID={worker_id}
export ORCHESTRATOR_WS_URL={orchestrator_ws}
export WORKER_TOKEN={worker_token}
export WORKER_PIPELINE_MODE=trellis
export CLOUD_PROVIDER={image_env.get('CLOUD_PROVIDER', 'intelion')}
if [ -n "${{TAILSCALE_AUTH_KEY:-}}" ]; then
  curl -fsSL https://tailscale.com/install.sh | sh || true
  tailscale up --authkey="$TAILSCALE_AUTH_KEY" --hostname="{worker_id}" || true
fi
docker pull ${{WORKER_DOCKER_IMAGE:-kwork-worker:latest}} || true
docker run -d --gpus all --restart unless-stopped --name kwork-worker \\
  -e ORCHESTRATOR_WS_URL -e WORKER_TOKEN -e WORKER_ID -e WORKER_PIPELINE_MODE \\
  -e MINIO_ENDPOINT -e MINIO_ACCESS_KEY -e MINIO_SECRET_KEY -e CLOUD_PROVIDER \\
  -e TAILSCALE_AUTH_KEY -e ORCHESTRATOR_WS_FALLBACK_URL \\
  ${{WORKER_DOCKER_IMAGE:-kwork-worker:latest}}
"""
