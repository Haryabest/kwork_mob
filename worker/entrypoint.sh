#!/bin/sh
# Tailscale (опционально) + авто-режим пайплайна + старт агента
set -eu

if [ -z "${WORKER_PIPELINE_MODE:-}" ]; then
  if [ -d /app/trellis ] && [ -f /app/trellis/setup.sh ]; then
    export WORKER_PIPELINE_MODE=trellis
  else
    export WORKER_PIPELINE_MODE=stub
  fi
fi

if [ "${ENVIRONMENT:-}" = "production" ]; then
  export WORKER_PIPELINE_MODE=trellis
  export TRELLIS_ALLOW_STUB_FALLBACK=0
fi

if [ -n "${TAILSCALE_AUTH_KEY:-}" ] && command -v tailscaled >/dev/null 2>&1; then
  tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
  sleep 1
  tailscale up --authkey="$TAILSCALE_AUTH_KEY" --hostname="${WORKER_ID:-worker}" || true
  # если задан Tailscale hostname оркестратора — предпочитаем его
  if [ -n "${ORCHESTRATOR_TS_HOST:-}" ]; then
    export ORCHESTRATOR_WS_URL="ws://${ORCHESTRATOR_TS_HOST}:8000/ws/worker"
  fi
fi

if [ -f /app/scripts/install_trellis_runtime.sh ]; then
  bash /app/scripts/install_trellis_runtime.sh || true
fi

exec "$@"
