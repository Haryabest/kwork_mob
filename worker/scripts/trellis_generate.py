"""Генерация 3D: TRELLIS.2 (production) или stub GLB (dev smoke)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_stub import write_minimal_glb
from pipeline_env import allow_stub_fallback, assert_production_pipeline, is_production_trellis


def main(task_dir: str) -> None:
    root = Path(task_dir)
    output = root / "raw_mesh.glb"
    mode = os.getenv("WORKER_PIPELINE_MODE", "trellis").lower()
    assert_production_pipeline()

    if mode == "trellis":
        try:
            from trellis_runtime import preflight_cuda, release_pipeline, run_trellis

            if is_production_trellis():
                preflight_cuda()
            try:
                staged = os.getenv("TRELLIS_STAGED_PIPELINE", "0").lower() in ("1", "true", "yes")
                if staged:
                    from trellis_staged import run_comfy_staged

                    run_comfy_staged(root, output)
                else:
                    run_trellis(root, output)
                print(f"[trellis_generate] TRELLIS.2 → {output} ({output.stat().st_size} bytes)")
            finally:
                release_pipeline()
            return
        except Exception as exc:
            try:
                from trellis_runtime import release_pipeline

                release_pipeline()
            except Exception:  # noqa: BLE001
                pass
            if allow_stub_fallback():
                print(f"[trellis_generate] fallback stub ({exc})")
                write_minimal_glb(output, root)
                return
            raise SystemExit(f"TRELLIS failed: {exc}") from exc

    write_minimal_glb(output, root)
    print(f"[trellis_generate] stub GLB → {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main(sys.argv[1])
