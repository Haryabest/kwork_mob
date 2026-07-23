#!/bin/sh
# setup.sh (flexgemm, nvdiffrast…) — только при docker run --gpus all.
set -eu

MARKER="/var/lib/worker/defer_trellis_runtime"
TRELLIS_ROOT="${TRELLIS_ROOT:-/app/trellis}"

[ -f "${MARKER}" ] || exit 0
command -v nvidia-smi >/dev/null 2>&1 || { echo "[trellis-runtime] нет nvidia-smi"; exit 0; }

python3 - <<'PY' || { echo "[trellis-runtime] CUDA недоступна"; exit 0; }
import sys

try:
    import torch

    sys.exit(0 if torch.cuda.is_available() else 1)
except Exception:
    sys.exit(1)
PY

echo "[trellis-runtime] GPU OK — setup.sh (basic + cuda extensions)"
cd "${TRELLIS_ROOT}"
export MAX_JOBS="${MAX_JOBS:-2}"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-${MAX_JOBS}}"
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-12.0}"

if [ -f setup.sh ]; then
  bash setup.sh --o-voxel --flexgemm --nvdiffrast --nvdiffrec
elif [ -d o-voxel ]; then
  pip3 install --no-cache-dir ./o-voxel --no-build-isolation
fi

python3 -c "import o_voxel; print('[trellis-runtime] o_voxel OK')"

PYTHONPATH="${TRELLIS_ROOT}:${PYTHONPATH:-}" python3 - <<'PY'
from trellis2.pipelines import Trellis2ImageTo3DPipeline  # noqa: F401

print("[trellis-runtime] Trellis2ImageTo3DPipeline OK")
PY

rm -f "${MARKER}"
echo "[trellis-runtime] готово"
