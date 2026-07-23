#!/usr/bin/env bash
# flexgemm требует GPU driver при import — ставим при старте контейнера, не при docker build.
set -euo pipefail

MARKER="/var/lib/worker/defer_flexgemm"
TRELLIS_ROOT="${TRELLIS_ROOT:-/app/trellis}"

[[ -f "${MARKER}" ]] || exit 0
command -v nvidia-smi >/dev/null 2>&1 || exit 0

python3 - <<'PY' || exit 0
import sys

try:
    import torch

    sys.exit(0 if torch.cuda.is_available() else 1)
except Exception:
    sys.exit(1)
PY

echo "[flexgemm] GPU доступен — setup.sh --flexgemm"
cd "${TRELLIS_ROOT}"
export MAX_JOBS="${MAX_JOBS:-2}"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-${MAX_JOBS}}"
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-12.0}"
bash setup.sh --flexgemm
rm -f "${MARKER}"
echo "[flexgemm] готово"
