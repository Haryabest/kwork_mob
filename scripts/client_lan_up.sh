#!/usr/bin/env bash
# Полный стек на GPU-сервере клиента в LAN (без ngrok).
# Usage:
#   cp .env.example .env   # задайте CLIENT_HOST
#   ./scripts/client_lan_up.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/client_lan_frontends.sh scripts/client_lan_up.sh 2>/dev/null || true

if [[ ! -f .env ]]; then
  echo "[client_lan] скопируйте .env.example → .env и задайте CLIENT_HOST" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

HOST="${CLIENT_HOST:-192.168.0.177}"
export API_BASE_URL="${API_BASE_URL:-http://${HOST}:8000}"
export SELLER_PUBLIC_URL="${SELLER_PUBLIC_URL:-http://${HOST}:3000}"
export MINIO_SSE_MODE="${MINIO_SSE_MODE:-none}"
export MINIO_PUBLIC_ENDPOINT="${MINIO_PUBLIC_ENDPOINT:-http://${HOST}:9010}"
# Воркер в отдельном контейнере: localhost из .env не достаёт до Redis на хосте
WORKER_REDIS_URL="${WORKER_REDIS_URL:-redis://host.docker.internal:6382/0}"
NOBG_CONFIDENCE="${NOBG_CONFIDENCE:-0.65}"

echo "[client_lan] HOST=$HOST"
echo "[client_lan] docker compose up…"
docker compose up -d postgres redis minio clickhouse orchestrator celery-worker celery-beat

echo "[client_lan] migrations…"
docker compose exec -T orchestrator alembic upgrade head
docker compose exec -T orchestrator python scripts/seed_staff.py || true

if docker image inspect kwork-worker:trellis2 >/dev/null 2>&1; then
  echo "[client_lan] GPU worker…"
  chmod +x "$ROOT/worker/entrypoint.sh" "$ROOT/worker/scripts/"*.sh 2>/dev/null || true
  docker volume create kwork_worker_state >/dev/null 2>&1 || true
  if docker ps -a --format '{{.Names}}' | grep -qx kwork-worker; then
    if [[ "${WORKER_FORCE_RECREATE:-0}" == "1" ]]; then
      docker rm -f kwork-worker 2>/dev/null || true
    else
      echo "[client_lan] воркер уже есть — restart (runtime не пересобирается)"
      docker start kwork-worker 2>/dev/null || docker restart kwork-worker
    fi
  fi
  if ! docker ps -a --format '{{.Names}}' | grep -qx kwork-worker; then
  docker run -d --gpus all --name kwork-worker --restart unless-stopped \
    --add-host=host.docker.internal:host-gateway \
    -v kwork_worker_state:/var/lib/worker \
    -v "$ROOT/worker/entrypoint.sh:/usr/local/bin/worker_entrypoint.sh:ro" \
    -v "$ROOT/worker/scripts:/app/scripts:ro" \
    -v "$ROOT/worker/worker_agent.py:/app/worker_agent.py:ro" \
    -e WORKER_ID="${WORKER_ID:-client-gpu-01}" \
    -e WORKER_TOKEN="${WORKER_TOKEN:-worker-dev-token}" \
    -e WORKER_PIPELINE_MODE="${WORKER_PIPELINE_MODE:-trellis}" \
    -e TRELLIS_ALLOW_STUB_FALLBACK="${TRELLIS_ALLOW_STUB_FALLBACK:-0}" \
    -e TRELLIS_VERSION=2 \
    -e TRELLIS2_PIPELINE_TYPE="${TRELLIS2_PIPELINE_TYPE:-512}" \
    -e TRELLIS2_LOW_VRAM="${TRELLIS2_LOW_VRAM:-1}" \
    -e ATTN_BACKEND="${ATTN_BACKEND:-xformers}" \
    -e ORCHESTRATOR_WS_URL="ws://host.docker.internal:8000/ws/worker" \
    -e ORCHESTRATOR_HTTP_URL="http://host.docker.internal:8000" \
    -e REDIS_URL="${WORKER_REDIS_URL}" \
    -e NOBG_CONFIDENCE="${NOBG_CONFIDENCE}" \
    -e MINIO_ENDPOINT="http://host.docker.internal:9010" \
    -e MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}" \
    -e MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}" \
    -e WATERMARK_HMAC_SECRET="${WATERMARK_HMAC_SECRET:-change-me-watermark-secret}" \
    kwork-worker:trellis2
  fi
else
  echo "[client_lan] образ kwork-worker:trellis2 не найден — воркер пропущен"
fi

cat <<EOF

=== Стек поднят ===
API:        http://${HOST}:8000/health
Swagger:    http://${HOST}:8000/api/docs
MinIO:      http://${HOST}:9010  (console :9011)
Grafana:    http://${HOST}:3003

Staff:      admin@example.com / admin1234  (ADMIN_2FA_REQUIRED=false в .env)

Фронты (одна команда, нужен Node 20+):
  ./scripts/client_lan_frontends.sh

Seller:     http://${HOST}:3000
Admin:      http://${HOST}:3001

Остановить фронты: ./scripts/client_lan_frontends.sh stop
Воркер:     docker logs -f kwork-worker
EOF
