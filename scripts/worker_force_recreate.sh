#!/usr/bin/env bash
# Пересоздать GPU-воркер с env из worker/.env.worker (не docker restart).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
docker rm -f kwork-worker 2>/dev/null || true
exec bash "$ROOT/scripts/worker_docker_apply.sh"
