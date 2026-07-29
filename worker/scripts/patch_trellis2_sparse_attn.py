"""TRELLIS.2 sparse attention: sdpa в env не поддерживается → xformers."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _target() -> Path:
    root = Path(os.getenv("TRELLIS_ROOT", "/app/trellis"))
    return root / "trellis2" / "modules" / "sparse" / "config.py"


def patch(path: Path) -> bool:
    if not path.is_file():
        print(f"[patch_sparse_attn] skip: {path} not found", file=sys.stderr)
        return False
    text = path.read_text(encoding="utf-8")
    old = (
        "    if env_sparse_attn_backend is not None and env_sparse_attn_backend in "
        "['xformers', 'flash_attn', 'flash_attn_3']:\n"
        "        ATTN = env_sparse_attn_backend"
    )
    new = (
        "    if env_sparse_attn_backend is not None:\n"
        "        if env_sparse_attn_backend == 'sdpa':\n"
        "            env_sparse_attn_backend = 'xformers'\n"
        "        if env_sparse_attn_backend in ['xformers', 'flash_attn', 'flash_attn_3']:\n"
        "            ATTN = env_sparse_attn_backend"
    )
    if old not in text:
        if "env_sparse_attn_backend == 'sdpa'" in text:
            print(f"[patch_sparse_attn] already patched: {path}")
            return True
        print(f"[patch_sparse_attn] pattern not found in {path}", file=sys.stderr)
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[patch_sparse_attn] patched {path}")
    return True


def main() -> None:
    ok = patch(_target())
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
