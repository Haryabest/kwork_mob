#!/usr/bin/env bash
# Установка TRELLIS.2 в production-образ воркера (§5.1).
# Вызывается из Dockerfile после git clone → /app/trellis.
set -euo pipefail

TRELLIS_ROOT="${1:-/app/trellis}"
DOWNLOAD_WEIGHTS="${DOWNLOAD_WEIGHTS:-1}"
TRELLIS_WEIGHTS="${TRELLIS_WEIGHTS:-microsoft/TRELLIS.2-4B}"
WEIGHTS_DIR="${TRELLIS_ROOT}/weights"

if [[ ! -d "${TRELLIS_ROOT}" ]]; then
  echo "[install_trellis2] ERROR: ${TRELLIS_ROOT} не найден" >&2
  exit 1
fi

cd "${TRELLIS_ROOT}"
export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-1200}"
export PIP_RETRIES="${PIP_RETRIES:-15}"
export MAX_JOBS="${MAX_JOBS:-2}"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-${MAX_JOBS}}"
export NINJAFLAGS="-j${MAX_JOBS}"
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-12.0}"

_install_basic_pip() {
  echo "[install_trellis2] базовые pip-зависимости"
  pip3 install --no-cache-dir \
    easydict opencv-python-headless trimesh transformers kornia timm zstandard \
    imageio imageio-ffmpeg tqdm ninja huggingface_hub
  pip3 install --no-cache-dir xformers || echo "[warn] xformers не установлен"
  pip3 install --no-cache-dir \
    "git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8" \
    || echo "[warn] utils3d не установлен"
}

_install_cumesh_o_voxel() {
  echo "[install_trellis2] cumesh + o-voxel (nvcc, без GPU driver)"
  if [[ -d o-voxel ]]; then
    pip3 install --no-cache-dir ./o-voxel --no-build-isolation
  else
    pip3 install --no-cache-dir o-voxel || true
  fi
  if ! python3 -c "import cumesh" 2>/dev/null; then
    pip3 install --no-cache-dir "git+https://github.com/JeffreyXiang/CuMesh.git" --no-build-isolation
  fi
}

_download_weights() {
  mkdir -p "${WEIGHTS_DIR}"
  if [[ "${DOWNLOAD_WEIGHTS}" != "1" ]]; then
    return 0
  fi
  echo "[install_trellis2] веса ${TRELLIS_WEIGHTS} → ${WEIGHTS_DIR}"
  if [[ -f scripts/download_weights.sh ]]; then
    bash scripts/download_weights.sh "${WEIGHTS_DIR}" || true
  elif [[ -f download_weights.py ]]; then
    python3 download_weights.py --out "${WEIGHTS_DIR}" || true
  else
    TRELLIS_WEIGHTS="${TRELLIS_WEIGHTS}" WEIGHTS_DIR="${WEIGHTS_DIR}" python3 - <<'PY'
import os
from pathlib import Path

repo = os.environ["TRELLIS_WEIGHTS"]
dest = Path(os.environ["WEIGHTS_DIR"])
try:
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=repo, local_dir=str(dest), local_dir_use_symlinks=False)
    print(f"[install_trellis2] HF snapshot → {dest}")
except Exception as exc:
    print(f"[warn] HF download: {exc}")
PY
  fi
}

_verify_build() {
  echo "[install_trellis2] verify cumesh + o_voxel"
  PYTHONPATH="${TRELLIS_ROOT}:${PYTHONPATH:-}" python3 - <<'PY'
import cumesh  # noqa: F401
import o_voxel  # noqa: F401

print("[install_trellis2] cumesh + o_voxel OK")
PY
  [[ -f trellis2/__init__.py ]] && echo "[install_trellis2] trellis2 package OK"
}

# docker build: без GPU driver — не трогаем requirements.txt/setup.sh (там flexgemm → torch.cuda)
if [[ "${DOCKER_BUILD:-}" == "1" ]]; then
  echo "[install_trellis2] режим docker build (без setup.sh / requirements.txt)"
  python3 - <<'PY'
import torch

cuda = getattr(torch.version, "cuda", None) or ""
print(f"[install_trellis2] torch {torch.__version__} cuda={cuda}")
PY
  mkdir -p /var/lib/worker
  touch /var/lib/worker/defer_trellis_runtime
  _install_basic_pip
  _install_cumesh_o_voxel
  _verify_build
  _download_weights
  echo "[install_trellis2] готово (runtime: setup.sh при старте контейнера)"
  exit 0
fi

echo "[install_trellis2] torch cu128 уже в образе — проверка"
python3 - <<'PY'
import sys
import torch

cuda = getattr(torch.version, "cuda", None) or ""
if "12.8" not in cuda:
    print(f"[warn] ожидался PyTorch cu128, получен cuda={cuda}", file=sys.stderr)
else:
    print(f"[install_trellis2] torch {torch.__version__} cuda={cuda}")
PY

echo "[install_trellis2] requirements.txt"
if [[ -f requirements.txt ]]; then
  pip3 install --no-cache-dir --timeout "${PIP_DEFAULT_TIMEOUT}" --retries "${PIP_RETRIES}" \
    -r requirements.txt
fi

if [[ -f setup.sh ]]; then
  echo "[install_trellis2] setup.sh (полный)"
  bash setup.sh --basic --nvdiffrast --nvdiffrec --cumesh --o-voxel --flexgemm
fi

_install_basic_pip
pip3 install --no-cache-dir o-voxel || true

if [[ -f setup.py ]] || [[ -f pyproject.toml ]]; then
  pip3 install --no-cache-dir --timeout "${PIP_DEFAULT_TIMEOUT}" --retries "${PIP_RETRIES}" \
    -e "${TRELLIS_ROOT}"
elif [[ -f trellis2/__init__.py ]]; then
  PYTHONPATH="${TRELLIS_ROOT}:${PYTHONPATH:-}" python3 -c "import trellis2; print('trellis2 OK')"
fi

_verify_build
_download_weights
echo "[install_trellis2] готово"
