"""Генерация 3D: TRELLIS.2 (production) или stub GLB (dev smoke)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_stub import write_minimal_glb
from pipeline_env import allow_stub_fallback, is_production_trellis


def main(task_dir: str) -> None:
    root = Path(task_dir)
    output = root / "raw_mesh.glb"
    mode = os.getenv("WORKER_PIPELINE_MODE", "trellis").lower()

    if mode == "trellis":
        try:
            from trellis_runtime import preflight_cuda, run_trellis

            if is_production_trellis():
                preflight_cuda()
            run_trellis(root, output)
            print(f"[trellis_generate] TRELLIS.2 → {output} ({output.stat().st_size} bytes)")
            return
        except Exception as exc:
            if allow_stub_fallback():
                print(f"[trellis_generate] fallback stub ({exc})")
                write_minimal_glb(output, root)
                return
            raise SystemExit(f"TRELLIS failed: {exc}") from exc

    write_minimal_glb(output, root)
    print(f"[trellis_generate] stub GLB → {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main(sys.argv[1])
