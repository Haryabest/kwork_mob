#!/bin/sh
# Пути кэша на volume /var/lib/worker — не теряются при docker rm.
set -eu

STATE="${WORKER_STATE_DIR:-/var/lib/worker}"
mkdir -p "${STATE}/cache" "${STATE}/torch" "${STATE}/triton" "${STATE}/nv/cuda" "${STATE}/nv/ComputeCache"

if [ -d /root/.cache/huggingface ]; then
  export HF_HOME=/root/.cache/huggingface
else
  export HF_HOME="${HF_HOME:-${STATE}/hf}"
  mkdir -p "${HF_HOME}"
fi

export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${HF_HOME}}"
export TORCH_HOME="${TORCH_HOME:-${STATE}/torch}"
export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-${STATE}/triton}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${STATE}/cache}"
export CUDA_CACHE_PATH="${CUDA_CACHE_PATH:-${STATE}/nv/cuda}"
export CUDA_CACHE_MAXSIZE="${CUDA_CACHE_MAXSIZE:-2147483647}"

if [ -n "${HF_TOKEN:-}" ]; then
  export HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-${HF_TOKEN}}"
fi

# Прогресс скачивания в docker logs (без TTY)
unset HF_HUB_DISABLE_PROGRESS_BARS 2>/dev/null || true
export HF_HUB_VERBOSITY="${HF_HUB_VERBOSITY:-info}"

mkdir -p "${TORCH_HOME}" "${TRITON_CACHE_DIR}" "${XDG_CACHE_HOME}" "${CUDA_CACHE_PATH}"

mkdir -p /root/.nv
if [ ! -e /root/.nv/ComputeCache ] || [ -L /root/.nv/ComputeCache ]; then
  ln -sfn "${STATE}/nv/ComputeCache" /root/.nv/ComputeCache 2>/dev/null || true
fi
