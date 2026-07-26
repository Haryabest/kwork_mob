#!/usr/bin/env bash
# Ручной apply GPU-воркера (тот же compose, что web-admin → Настройка TRELLIS).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ENV_FILE="${WORKER_DEPLOY_ENV_FILE:-worker/.env.worker}"
COMPOSE_FILE="${WORKER_DEPLOY_COMPOSE_FILE:-worker/docker-compose.worker.yml}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Нет $ENV_FILE — сначала сохраните настройки в web-admin" >&2
  exit 1
fi
exec docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --force-recreate worker
