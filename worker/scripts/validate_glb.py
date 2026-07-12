"""Финальная валидация GLB: размер, наличие HMAC."""

from __future__ import annotations

import sys
from pathlib import Path

MAX_BYTES = 15 * 1024 * 1024


def main(task_dir: str) -> None:
    root = Path(task_dir)
    model = root / "model.glb"
    if not model.exists():
        raise SystemExit("model.glb missing")
    size = model.stat().st_size
    if size <= 12:
        raise SystemExit(f"model.glb too small: {size}")
    if size > MAX_BYTES:
        raise SystemExit(f"model.glb too large: {size} > {MAX_BYTES}")
    magic = model.read_bytes()[:4]
    if magic != b"glTF":
        raise SystemExit(f"invalid GLB magic: {magic!r}")
    hmac_file = root / "watermark.hmac"
    if not hmac_file.exists():
        raise SystemExit("watermark.hmac missing")
    print(f"[validate_glb] ok size={size}")


if __name__ == "__main__":
    main(sys.argv[1])
