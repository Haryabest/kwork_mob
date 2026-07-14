#!/usr/bin/env python3
"""CLI: Intelion Cloud GPU-воркеры (§14.7). TRELLIS собирается на VM, не на ПК."""

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
    cloud_env_int,
    list_providers,
    worker_bootstrap_script,
)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def write_worker_env(path: Path) -> None:
    content = f"""# Автоген worker/cloud/provision.py — локальный stub-воркер
ORCHESTRATOR_WS_URL={_env("ORCHESTRATOR_WS_URL", "ws://localhost:8000/ws/worker")}
ORCHESTRATOR_WS_FALLBACK_URL={_env("ORCHESTRATOR_WS_FALLBACK_URL")}
WORKER_TOKEN={_env("WORKER_TOKEN", "worker-dev-token")}
WORKER_ID={_env("WORKER_ID", "local-stub-01")}
WORKER_PIPELINE_MODE=stub
MINIO_ENDPOINT={_env("MINIO_ENDPOINT", "http://localhost:9010")}
MINIO_ACCESS_KEY={_env("MINIO_ACCESS_KEY", "minioadmin")}
MINIO_SECRET_KEY={_env("MINIO_SECRET_KEY", "minioadmin")}
REDIS_URL={_env("REDIS_URL", "redis://localhost:6382/0")}
CLOUD_PROVIDER={_env("CLOUD_PROVIDER", "intelion")}
"""
    path.write_text(content, encoding="utf-8")
    print(f"Записан {path}")


def _print_bootstrap_hint(inst, script: str) -> None:
    ip = inst.public_ip or "?"
    login = inst.login or "root"
    print(f"\n--- Bootstrap TRELLIS on VM ({inst.provider}) ---")
    print(f"1. Пароль: python worker/cloud/provision.py --action password --instance-id {inst.id}")
    print(f"2. SSH: ssh {login}@{ip}")
    print("3. Сохраните и запустите bootstrap.sh на VM:")
    print(f"   scp bootstrap-{inst.id}.sh {login}@{ip}:/tmp/bootstrap.sh")
    print("   chmod +x /tmp/bootstrap.sh && sudo /tmp/bootstrap.sh")
    out = Path(f"bootstrap-{inst.id}.sh")
    out.write_text(script, encoding="utf-8")
    print(f"   (скрипт записан локально: {out})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Intelion Cloud GPU + TRELLIS.2")
    parser.add_argument(
        "--action",
        choices=["status", "env", "providers", "flavors", "os-images", "create", "start", "stop", "get", "password"],
        default="status",
    )
    parser.add_argument("--gpu", default="rtx4090", help="slug для поиска flavor (или INTELION_FLAVOR_ID)")
    parser.add_argument("--flavor-id", type=int, default=None)
    parser.add_argument("--os-id", type=int, default=None)
    parser.add_argument("--ssd-gb", type=int, default=None)
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
        print("  Локально: WORKER_PIPELINE_MODE=stub (без TRELLIS)")
        print("  GPU/TRELLIS: только Intelion → bootstrap.sh на VM")
        return 0

    if args.action == "providers":
        for p in list_providers():
            print(p)
        return 0

    if args.action == "flavors":
        for f in client.list_flavors():
            print(f)
        return 0

    if args.action == "os-images":
        fid = args.flavor_id or cloud_env_int(provider, "FLAVOR_ID")
        for img in client.list_os_images(flavor_id=fid):
            print(img)
        return 0

    try:
        if args.action == "create":
            write_worker_env(env_path)
            for i in range(args.count):
                wid = args.worker_id or f"{provider}-{args.gpu}-{i + 1}"
                bootstrap = worker_bootstrap_script(
                    worker_id=wid,
                    orchestrator_ws=_env("ORCHESTRATOR_WS_URL", "wss://orchestrator/ws/worker"),
                    worker_token=_env("WORKER_TOKEN", "worker-dev-token"),
                    image_env={
                        "CLOUD_PROVIDER": provider,
                        "MINIO_ENDPOINT": _env("MINIO_ENDPOINT"),
                        "MINIO_ACCESS_KEY": _env("MINIO_ACCESS_KEY"),
                        "MINIO_SECRET_KEY": _env("MINIO_SECRET_KEY"),
                        "TAILSCALE_AUTH_KEY": _env("TAILSCALE_AUTH_KEY"),
                        "ORCHESTRATOR_WS_FALLBACK_URL": _env("ORCHESTRATOR_WS_FALLBACK_URL"),
                        "WORKER_GIT_REPO": _env("WORKER_GIT_REPO"),
                        "WORKER_GIT_BRANCH": _env("WORKER_GIT_BRANCH", "main"),
                    },
                )
                inst = client.create_instance(
                    gpu=args.gpu,
                    image=_env("WORKER_DOCKER_IMAGE", "kwork-worker:trellis2"),
                    worker_id=wid,
                    user_data=bootstrap,
                    flavor_id=args.flavor_id,
                    os_id=args.os_id,
                    ssd_gb=args.ssd_gb,
                )
                print(
                    f"CREATED id={inst.id} status={inst.status} ip={inst.public_ip} login={inst.login}"
                )
                _print_bootstrap_hint(inst, bootstrap)
            return 0

        if args.action == "get":
            if not args.instance_id:
                print("--instance-id required", file=sys.stderr)
                return 2
            inst = client.get_instance(args.instance_id)
            print(inst)
            return 0

        if args.action == "password":
            if not args.instance_id:
                print("--instance-id required", file=sys.stderr)
                return 2
            pwd = client.get_password(args.instance_id)
            print(pwd or "(пароль ещё не готов — подождите 2–5 мин после create)")
            return 0

        if args.action == "start":
            if not args.instance_id:
                print("--instance-id required", file=sys.stderr)
                return 2
            inst = client.start_instance(args.instance_id)
            print(f"STARTED id={inst.id} status={inst.status} ip={inst.public_ip}")
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
