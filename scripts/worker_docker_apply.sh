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
# Compose подставляет ${REDIS_URL} из shell раньше, чем из --env-file
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"
  line="${line//$'\r'/}"
  [[ "$line" =~ ^[[:space:]]*$ ]] && continue
  key="${line%%=*}"
  key="${key%"${key##*[![:space:]]}"}"
  key="${key#"${key%%[![:space:]]*}"}"
  [[ -n "$key" ]] && unset "$key" 2>/dev/null || true
done < "$ENV_FILE"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --force-recreate worker
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T worker \
  bash /app/scripts/install_gltf_transform.sh || true
