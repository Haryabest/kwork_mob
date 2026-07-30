#!/bin/sh
# Tailscale (опционально) + авто-режим пайплайна + старт агента
set -eu

if [ -f /app/scripts/setup_worker_cache.sh ]; then
  # shellcheck disable=SC1091
  . /app/scripts/setup_worker_cache.sh
fi

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
  if [ "${WORKER_PIPELINE_MODE:-}" = "trellis" ] && [ "${TRELLIS_ALLOW_STUB_FALLBACK:-0}" != "1" ]; then
    bash /app/scripts/install_trellis_runtime.sh
  else
    bash /app/scripts/install_trellis_runtime.sh || true
  fi
fi

if [ -f /app/scripts/install_gltf_transform.sh ]; then
  bash /app/scripts/install_gltf_transform.sh || true
fi

if [ -f /app/scripts/prefetch_worker_models.sh ]; then
  bash /app/scripts/prefetch_worker_models.sh || true
fi

if [ -f /app/scripts/extract_dinov3_from_cache.py ]; then
  python3 /app/scripts/extract_dinov3_from_cache.py || true
fi

if [ -f /app/scripts/warmup_gpu_cache.sh ]; then
  bash /app/scripts/warmup_gpu_cache.sh || true
fi

# ComfyUI RMBG: сброс устаревших -e из ручного docker run
if [ "${NOBG_RESET_COMFY_DEFAULTS:-1}" != "0" ]; then
  export NOBG_ENGINE="${NOBG_ENGINE:-rmbg2}"
  export NOBG_FALLBACK_LEGACY=0
  export NOBG_SENSITIVITY="${NOBG_SENSITIVITY:-1.0}"
  export NOBG_INPUT_SIZE="${NOBG_INPUT_SIZE:-1024}"
  export NOBG_MIN_RATIO="${NOBG_MIN_RATIO:-0.05}"
  export NOBG_STRICT_SEGMENTATION="${NOBG_STRICT_SEGMENTATION:-0}"
  export NOBG_CONFIDENCE="${NOBG_CONFIDENCE:-0.80}"
  unset NOBG_MASK_THRESHOLD
fi

exec "$@"
