#!/usr/bin/env python3
"""CLI create/start/stop облачных GPU-воркеров Intelion / Immers (§14.7 / §11.3.3)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cloud.providers import (  # noqa: E402
    PROVIDERS,
    CloudProviderClient,
    CloudProviderError,
    cloud_user_data,
)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def write_worker_env(path: Path) -> None:
    content = f"""# Автоген worker/cloud/provision.py
ORCHESTRATOR_WS_URL={_env("ORCHESTRATOR_WS_URL", "ws://localhost:8000/ws/worker")}
ORCHESTRATOR_WS_FALLBACK_URL={_env("ORCHESTRATOR_WS_FALLBACK_URL")}
WORKER_TOKEN={_env("WORKER_TOKEN", "worker-dev-token")}
WORKER_ID={_env("WORKER_ID", "cloud-gpu-01")}
WORKER_PIPELINE_MODE=trellis
MINIO_ENDPOINT={_env("MINIO_ENDPOINT", "http://localhost:9010")}
MINIO_ACCESS_KEY={_env("MINIO_ACCESS_KEY", "minioadmin")}
MINIO_SECRET_KEY={_env("MINIO_SECRET_KEY", "minioadmin")}
CLOUD_PROVIDER={_env("CLOUD_PROVIDER", "intelion")}
TAILSCALE_AUTH_KEY={_env("TAILSCALE_AUTH_KEY")}
WORKER_DOCKER_IMAGE={_env("WORKER_DOCKER_IMAGE", "kwork-worker:latest")}
"""
    path.write_text(content, encoding="utf-8")
    print(f"Записан {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Облачный GPU-воркер Intelion/Immers")
    parser.add_argument(
        "--action",
        choices=["status", "env", "flavors", "create", "start", "stop", "get"],
        default="status",
    )
    parser.add_argument("--gpu", default="rtx4090")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--instance-id", default="")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--worker-id", default=None)
    args = parser.parse_args()

    provider = (args.provider or _env("CLOUD_PROVIDER", "intelion")).lower()
    if provider not in PROVIDERS:
        print(f"Неизвестный провайдер: {provider}", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env.worker"
    client = CloudProviderClient(provider)

    if args.action == "env":
        write_worker_env(env_path)
        return 0

    if args.action == "status":
        meta = PROVIDERS[provider]
        print(f"Провайдер: {provider}")
        print(f"  API: {client.base}")
        print(f"  Token: {'задан' if client.token else 'НЕ ЗАДАН'}")
        print(f"  Mock: {client.mock}")
        print(f"  Stop mode: {meta['stop_mode']}")
        return 0

    if args.action == "flavors":
        for f in client.list_flavors():
            print(f)
        return 0

    try:
        if args.action == "create":
            write_worker_env(env_path)
            for i in range(args.count):
                wid = args.worker_id or f"cloud-{provider}-{_env('WORKER_ID', 'gpu')}-{i+1}"
                ud = cloud_user_data(
                    worker_id=wid,
                    orchestrator_ws=_env("ORCHESTRATOR_WS_URL", "wss://orchestrator/ws/worker"),
                    worker_token=_env("WORKER_TOKEN", "worker-dev-token"),
                    image_env={
                        "CLOUD_PROVIDER": provider,
                        "MINIO_ENDPOINT": _env("MINIO_ENDPOINT"),
                        "MINIO_ACCESS_KEY": _env("MINIO_ACCESS_KEY"),
                        "MINIO_SECRET_KEY": _env("MINIO_SECRET_KEY"),
                        "TAILSCALE_AUTH_KEY": _env("TAILSCALE_AUTH_KEY"),
                        "WORKER_DOCKER_IMAGE": _env("WORKER_DOCKER_IMAGE", "kwork-worker:latest"),
                        "ORCHESTRATOR_WS_FALLBACK_URL": _env("ORCHESTRATOR_WS_FALLBACK_URL"),
                    },
                )
                inst = client.create_instance(
                    gpu=args.gpu,
                    image=_env("WORKER_DOCKER_IMAGE", "kwork-worker:latest"),
                    worker_id=wid,
                    user_data=ud,
                )
                print(f"CREATED id={inst.id} status={inst.status} ts={inst.tailscale_ip} ip={inst.public_ip}")
            return 0

        if args.action == "get":
            if not args.instance_id:
                print("--instance-id required", file=sys.stderr)
                return 2
            inst = client.get_instance(args.instance_id)
            print(inst)
            return 0

        if args.action == "start":
            if not args.instance_id:
                print("--instance-id required", file=sys.stderr)
                return 2
            inst = client.start_instance(args.instance_id)
            print(f"STARTED id={inst.id} status={inst.status}")
            return 0

        if args.action == "stop":
            if not args.instance_id:
                print("--instance-id required", file=sys.stderr)
                return 2
            res = client.stop_instance(args.instance_id)
            print(f"STOPPED {res}")
            return 0
    except CloudProviderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
