"""Однократный прогрев GPU: загрузка TRELLIS + nobg, кэш ядер CUDA на диск."""

from __future__ import annotations

import os
import sys
from pathlib import Path

SIG_PATH = Path("/var/lib/worker/gpu_warmup_sig")


def _signature() -> str:
    keys = (
        "TRELLIS_VERSION",
        "TRELLIS_WEIGHTS",
        "TRELLIS2_PIPELINE_TYPE",
        "TRELLIS2_LOW_VRAM",
        "NOBG_ENGINE",
        "NOBG_MODEL_ID",
        "ATTN_BACKEND",
        "TORCH_CUDA_ARCH_LIST",
    )
    return "|".join(f"{k}={os.getenv(k, '')}" for k in keys)


def _warm_trellis() -> None:
    sys.path.insert(0, "/app/scripts")
    from trellis_runtime import get_pipeline, release_pipeline

    print("[warmup] TRELLIS: загрузка весов…", flush=True)
    get_pipeline()
    print("[warmup] TRELLIS: release VRAM", flush=True)
    release_pipeline()


def _warm_nobg() -> None:
    sys.path.insert(0, "/app/scripts")
    from remove_background import warmup_nobg

    print("[warmup] nobg…", flush=True)
    warmup_nobg()


def main() -> int:
    if (os.getenv("WORKER_PIPELINE_MODE") or "stub").strip().lower() != "trellis":
        print("[warmup] skip (not trellis)", flush=True)
        return 0

    sig = _signature()
    if SIG_PATH.is_file() and SIG_PATH.read_text(encoding="utf-8").strip() == sig:
        if os.getenv("WORKER_GPU_WARMUP_FORCE", "0") not in ("1", "true", "yes"):
            print("[warmup] уже готово", flush=True)
            return 0

    try:
        import torch

        if not torch.cuda.is_available():
            print("[warmup] skip (no CUDA)", flush=True)
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[warmup] skip (torch): {exc}", flush=True)
        return 0

    _warm_nobg()
    _warm_trellis()

    SIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SIG_PATH.write_text(sig, encoding="utf-8")
    print("[warmup] готово", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[warmup] FAILED: {exc}", flush=True)
        raise
