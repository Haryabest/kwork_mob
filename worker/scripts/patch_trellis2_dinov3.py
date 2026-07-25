"""Patch TRELLIS.2 DINOv3 extractor for transformers >= 5.0 (microsoft/TRELLIS.2#147)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _target() -> Path:
    root = Path(os.getenv("TRELLIS_ROOT", "/app/trellis"))
    return root / "trellis2" / "modules" / "image_feature_extractor.py"


def patch(path: Path) -> bool:
    if not path.is_file():
        print(f"[patch_dinov3] skip: {path} not found", file=sys.stderr)
        return False
    text = path.read_text(encoding="utf-8")
    if "inner_model = getattr(self.model, \"model\", self.model)" in text:
        print(f"[patch_dinov3] already patched: {path}")
        return True
    old = "for i, layer_module in enumerate(self.model.layer):"
    new = (
        "inner_model = getattr(self.model, \"model\", self.model)\n"
        "        for i, layer_module in enumerate(inner_model.layer):"
    )
    if old not in text:
        print(f"[patch_dinov3] pattern not found in {path}", file=sys.stderr)
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[patch_dinov3] patched {path}")
    return True


def main() -> None:
    ok = patch(_target())
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
