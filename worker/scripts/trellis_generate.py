"""Генерация 3D через TRELLIS (12 multi-view фото) или stub GLB."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_stub import write_minimal_glb


def main(task_dir: str) -> None:
    root = Path(task_dir)
    output = root / "raw_mesh.glb"
    mode = os.getenv("WORKER_PIPELINE_MODE", "trellis").lower()

    if mode == "trellis":
        try:
            from trellis_runtime import run_trellis

            run_trellis(root, output)
            print(f"[trellis_generate] TRELLIS → {output} ({output.stat().st_size} bytes)")
            return
        except Exception as exc:
            # В production trellis-режиме не молча подменяем stub — падаем
            if os.getenv("TRELLIS_ALLOW_STUB_FALLBACK", "0") == "1":
                print(f"[trellis_generate] fallback stub ({exc})")
                write_minimal_glb(output)
                return
            raise SystemExit(f"TRELLIS failed: {exc}") from exc

    write_minimal_glb(output)
    print(f"[trellis_generate] stub GLB → {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main(sys.argv[1])
