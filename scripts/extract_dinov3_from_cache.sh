#!/usr/bin/env bash
# DINOv3 из уже скачанного HF-кэша — без токена.
# Usage:
#   ./scripts/extract_dinov3_from_cache.sh
#   ./scripts/extract_dinov3_from_cache.sh --worker
set -euo pipefail

IMPORT_WORKER=0
HF_CACHE="${HF_CACHE:-$HOME/hf_cache}"
WORKER="${WORKER_CONTAINER:-kwork-worker}"

for arg in "$@"; do
  [[ "$arg" == "--worker" ]] && IMPORT_WORKER=1
done

OUT_DIR="${DINOV3_OUT_DIR:-$HOME/dinov3-vitl16}"
mkdir -p "${HF_CACHE}" "${OUT_DIR}"

echo "[extract] ищем dinov3 в ${HF_CACHE}..."
if ! docker run --rm \
  -v "${HF_CACHE}:/root/.cache/huggingface:ro" \
  -v "$(pwd)/worker/scripts/extract_dinov3_from_cache.py:/tmp/extract.py:ro" \
  -v "${OUT_DIR}:/out" \
  -e DINOV3_OUT=/out \
  python:3.11-slim \
  python3 /tmp/extract.py; then
  echo "[extract] в кэше нет dinov3. Проверьте на 192.168.0.177:" >&2
  echo "  ls ~/hf_cache/hub/models--facebook--dinov3-vitl16-pretrain-lvd1689m/snapshots/" >&2
  exit 1
fi

if [[ "${IMPORT_WORKER}" == "1" ]]; then
  docker exec "${WORKER}" mkdir -p /var/lib/worker/dinov3-vitl16
  docker cp "${OUT_DIR}/." "${WORKER}:/var/lib/worker/dinov3-vitl16/"
  docker restart "${WORKER}"
  echo "[extract] → ${WORKER}:/var/lib/worker/dinov3-vitl16"
fi
