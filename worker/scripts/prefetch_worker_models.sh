#!/bin/sh
# Скачать веса HF один раз (маркер в volume kwork_worker_state).
set -eu

MARKER="/var/lib/worker/models_prefetched"
mkdir -p /var/lib/worker

if [ -f "${MARKER}" ] && [ "${WORKER_PREFETCH_FORCE:-0}" != "1" ]; then
  echo "[prefetch] кэш моделей уже готов (${MARKER})"
  exit 0
fi

if [ "${WORKER_PIPELINE_MODE:-stub}" != "trellis" ]; then
  echo "[prefetch] skip (WORKER_PIPELINE_MODE=${WORKER_PIPELINE_MODE:-stub})"
  exit 0
fi

echo "[prefetch] pip: transformers huggingface_hub …"
pip3 install --no-cache-dir -q 'transformers>=4.44.0' 'huggingface_hub>=0.23.0' 'kornia>=0.7.0' || true

python3 /app/scripts/prefetch_worker_models.py
touch "${MARKER}"
echo "[prefetch] готово → ${MARKER}"
