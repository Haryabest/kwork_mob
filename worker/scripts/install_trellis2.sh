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

INSTALL_FLASH_ATTN="${INSTALL_FLASH_ATTN:-0}"
# Ограничиваем параллельную компиляцию — иначе Docker/WSL падает с EOF (OOM).
export MAX_JOBS="${MAX_JOBS:-2}"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-${MAX_JOBS}}"
export NINJAFLAGS="-j${MAX_JOBS}"

echo "[install_trellis2] setup.sh (без --flash-attn, без --new-env)"
if [[ -f setup.sh ]]; then
  bash setup.sh --basic --nvdiffrast --nvdiffrec --cumesh --o-voxel --flexgemm
fi

echo "[install_trellis2] доп. зависимости TRELLIS.2"
pip3 install --no-cache-dir \
  easydict opencv-python-headless trimesh transformers kornia timm zstandard \
  imageio imageio-ffmpeg tqdm ninja
pip3 install --no-cache-dir huggingface_hub
pip3 install --no-cache-dir xformers || echo "[warn] xformers не установлен — нужен ATTN_BACKEND=xformers"
if [[ "${INSTALL_FLASH_ATTN}" == "1" ]]; then
  echo "[install_trellis2] flash-attn (долго, нужно ≥16 GB RAM Docker)"
  pip3 install --no-cache-dir flash-attn --no-build-isolation \
    || echo "[warn] flash-attn не собрался"
else
  echo "[install_trellis2] flash-attn пропущен (INSTALL_FLASH_ATTN=0, ATTN_BACKEND=xformers)"
fi
pip3 install --no-cache-dir o-voxel || echo "[warn] o-voxel pip — возможно уже из setup.sh"

echo "[install_trellis2] пакет trellis2 (TRELLIS.2 без setup.py — только PYTHONPATH)"
if [[ -f setup.py ]] || [[ -f pyproject.toml ]]; then
  pip3 install --no-cache-dir --timeout "${PIP_DEFAULT_TIMEOUT}" --retries "${PIP_RETRIES}" \
    -e "${TRELLIS_ROOT}"
elif [[ -f trellis2/__init__.py ]]; then
  PYTHONPATH="${TRELLIS_ROOT}:${PYTHONPATH:-}" python3 - <<'PY'
import sys
from pathlib import Path

root = Path(".").resolve()
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
import trellis2  # noqa: F401

print(f"[install_trellis2] trellis2 OK ({root / 'trellis2'})")
PY
else
  echo "[install_trellis2] ERROR: нет trellis2/ в ${TRELLIS_ROOT} — git clone не удался?" >&2
  ls -la "${TRELLIS_ROOT}" >&2 || true
  exit 1
fi

echo "[install_trellis2] verify cumesh + trellis2 pipeline"
PYTHONPATH="${TRELLIS_ROOT}:${PYTHONPATH:-}" python3 - <<'PY'
import cumesh  # noqa: F401
import o_voxel  # noqa: F401
from trellis2.pipelines import Trellis2ImageTo3DPipeline  # noqa: F401

print("[install_trellis2] cumesh + Trellis2ImageTo3DPipeline OK")
PY

mkdir -p "${WEIGHTS_DIR}"

if [[ "${DOWNLOAD_WEIGHTS}" == "1" ]]; then
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
fi

echo "[install_trellis2] готово"
