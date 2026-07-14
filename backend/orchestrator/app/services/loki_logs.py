"""Docker/Loki logs для панели хранения §11.16.4."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_CONTAINERS = (
    "postgres",
    "minio",
    "patroni",
    "redis",
    "clickhouse",
    "orchestrator",
    "haproxy",
)


def configured_containers() -> list[str]:
    raw = (getattr(settings, "DOCKER_LOG_CONTAINERS", "") or "").strip()
    if raw:
        return [c.strip() for c in raw.split(",") if c.strip()]
    return list(DEFAULT_CONTAINERS)


def _loki_base() -> str:
    return (getattr(settings, "LOKI_URL", "") or "").rstrip("/")


def _docker_proxy() -> str:
    return (getattr(settings, "DOCKER_LOGS_PROXY_URL", "") or "").rstrip("/")


def _parse_loki_streams(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    results = (data.get("data") or {}).get("result") or []
    for stream in results:
        labels = stream.get("stream") or {}
        for ts_ns, line in stream.get("values") or []:
            try:
                ts = datetime.fromtimestamp(int(ts_ns) / 1e9, tz=timezone.utc)
            except (TypeError, ValueError):
                ts = datetime.now(timezone.utc)
            items.append(
                {
                    "timestamp": ts.isoformat(),
                    "message": line,
                    "labels": labels,
                    "level": "INFO",
                    "source": "docker",
                }
            )
    items.sort(key=lambda r: r["timestamp"], reverse=True)
    return items


async def fetch_container_logs(
    *,
    container: str,
    limit: int = 200,
    minutes: int = 60,
) -> dict[str, Any]:
    """Логи контейнера через Loki LogQL или docker-logs proxy."""
    name = (container or "").strip()
    allowed = configured_containers()
    if not name:
        return {
            "ok": False,
            "backend": "none",
            "containers": allowed,
            "items": [],
            "error": "container required",
        }

    limit = max(1, min(int(limit), 2000))
    minutes = max(1, min(int(minutes), 24 * 60))
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes)

    loki = _loki_base()
    if loki:
        query = '{container="' + name.replace('"', "") + '"}'
        params = {
            "query": query,
            "limit": str(limit),
            "start": str(int(start.timestamp() * 1e9)),
            "end": str(int(now.timestamp() * 1e9)),
            "direction": "backward",
        }
        url = f"{loki}/loki/api/v1/query_range?{urlencode(params)}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(url)
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "backend": "loki",
                    "container": name,
                    "containers": allowed,
                    "items": [],
                    "error": resp.text[:400],
                }
            items = _parse_loki_streams(resp.json())[:limit]
            return {
                "ok": True,
                "backend": "loki",
                "container": name,
                "containers": allowed,
                "items": items,
                "from": start.isoformat(),
                "to": now.isoformat(),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("loki query failed: %s", exc)
            return {
                "ok": False,
                "backend": "loki",
                "container": name,
                "containers": allowed,
                "items": [],
                "error": str(exc)[:300],
            }

    proxy = _docker_proxy()
    if proxy:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{proxy}/logs",
                    json={"container": name, "tail": limit, "minutes": minutes},
                )
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "backend": "docker_proxy",
                    "container": name,
                    "containers": allowed,
                    "items": [],
                    "error": resp.text[:400],
                }
            body = resp.json()
            raw_lines = body.get("lines") or body.get("items") or []
            items = []
            for i, line in enumerate(raw_lines[:limit]):
                if isinstance(line, dict):
                    items.append(
                        {
                            "timestamp": line.get("timestamp") or now.isoformat(),
                            "message": line.get("message") or str(line),
                            "level": line.get("level") or "INFO",
                            "source": "docker",
                            "labels": {"container": name},
                        }
                    )
                else:
                    items.append(
                        {
                            "timestamp": (now - timedelta(seconds=i)).isoformat(),
                            "message": str(line),
                            "level": "INFO",
                            "source": "docker",
                            "labels": {"container": name},
                        }
                    )
            return {
                "ok": True,
                "backend": "docker_proxy",
                "container": name,
                "containers": allowed,
                "items": items,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "backend": "docker_proxy",
                "container": name,
                "containers": allowed,
                "items": [],
                "error": str(exc)[:300],
            }

    return {
        "ok": True,
        "backend": "mock",
        "container": name,
        "containers": allowed,
        "items": [
            {
                "timestamp": now.isoformat(),
                "message": (
                    f"[mock] Configure LOKI_URL or DOCKER_LOGS_PROXY_URL для логов «{name}». "
                    "§11.16.4 docker logs / Loki."
                ),
                "level": "INFO",
                "source": "docker",
                "labels": {"container": name},
            }
        ],
        "hint": "Set LOKI_URL or DOCKER_LOGS_PROXY_URL",
    }
