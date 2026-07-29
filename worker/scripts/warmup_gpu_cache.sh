#!/bin/sh
# Прогрев GPU в фоне при старте (маркер + сигнатура env в volume).
set -eu

if [ "${WORKER_STARTUP_WARMUP:-1}" = "0" ] || [ "${WORKER_STARTUP_WARMUP:-1}" = "false" ]; then
  echo "[warmup] отключён (WORKER_STARTUP_WARMUP=0)"
  exit 0
fi

if [ "${WORKER_PIPELINE_MODE:-stub}" != "trellis" ]; then
  exit 0
fi

command -v nvidia-smi >/dev/null 2>&1 || exit 0

python3 /app/scripts/warmup_gpu_cache.py &
echo "[warmup] фоновый прогрев GPU (pid $!)"
