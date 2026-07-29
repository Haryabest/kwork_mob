#!/usr/bin/env bash
# Скачать DINOv3 в volume и (опционально) скопировать на GPU-воркер.
# Usage:
#   export HF_TOKEN=hf_...
#   ./scripts/download_dinov3_docker.sh
#   ./scripts/download_dinov3_docker.sh --import-to-worker
set -euo pipefail

IMPORT_WORKER=0
OUT_DIR="${DINOV3_OUT_DIR:-$HOME/dinov3-vitl16}"
ARCHIVE="${DINOV3_ARCHIVE:-$HOME/dinov3.tgz}"
WORKER_NAME="${WORKER_CONTAINER:-kwork-worker}"
IMAGE="${DINOV3_DOCKER_IMAGE:-python:3.11-slim}"

for arg in "$@"; do
  case "$arg" in
    --import-to-worker) IMPORT_WORKER=1 ;;
  esac
done

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "Задайте HF_TOKEN: export HF_TOKEN=hf_..." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

echo "[dinov3] download → ${OUT_DIR}"
docker run --rm \
  -v "${OUT_DIR}:/out" \
  -e HF_TOKEN="${HF_TOKEN}" \
  "${IMAGE}" \
  bash -c 'pip install -q "huggingface_hub[cli]" && hf download facebook/dinov3-vitl16-pretrain-lvd1689m --local-dir /out --token "$HF_TOKEN"'

echo "[dinov3] tar → ${ARCHIVE}"
tar czf "${ARCHIVE}" -C "$(dirname "${OUT_DIR}")" "$(basename "${OUT_DIR}")"
ls -lh "${ARCHIVE}"

if [[ "${IMPORT_WORKER}" == "1" ]]; then
  echo "[dinov3] docker cp → ${WORKER_NAME}:/var/lib/worker/dinov3-vitl16"
  docker exec "${WORKER_NAME}" mkdir -p /var/lib/worker/dinov3-vitl16
  docker cp "${OUT_DIR}/." "${WORKER_NAME}:/var/lib/worker/dinov3-vitl16/"
  docker restart "${WORKER_NAME}"
  echo "[dinov3] готово. Проверка: docker logs -f ${WORKER_NAME} | grep dinov3-local"
fi
