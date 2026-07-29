#!/usr/bin/env python3
"""Скопировать DINOv3 из HF-кэша в /var/lib/worker/dinov3-vitl16 (без токена, offline)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

REPO = "facebook/dinov3-vitl16-pretrain-lvd1689m"
CACHE_NAME = "models--" + REPO.replace("/", "--")
DEFAULT_OUT = Path("/var/lib/worker/dinov3-vitl16")


def _cache_roots() -> list[Path]:
    roots: list[Path] = []
    for raw in (
        os.getenv("HF_HOME", ""),
        os.getenv("HUGGINGFACE_HUB_CACHE", ""),
        "/root/.cache/huggingface",
        str(Path.home() / ".cache" / "huggingface"),
    ):
        if raw:
            roots.append(Path(raw).expanduser())
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r.resolve()) if r.exists() else str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _find_snapshot() -> Path | None:
    for root in _cache_roots():
        hub = root / "hub" / CACHE_NAME / "snapshots"
        if not hub.is_dir():
            continue
        snaps = sorted(hub.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for snap in snaps:
            if (snap / "config.json").is_file():
                return snap
    return None


def main() -> int:
    out = Path(os.getenv("DINOV3_OUT", str(DEFAULT_OUT))).expanduser()
    snap = _find_snapshot()
    if snap is None:
        print("[extract_dinov3] не найден в HF-кэше", file=sys.stderr)
        print(f"[extract_dinov3] искали: {CACHE_NAME}", file=sys.stderr)
        for root in _cache_roots():
            print(f"  - {root / 'hub' / CACHE_NAME}", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    for item in snap.iterdir():
        dest = out / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    if not (out / "config.json").is_file():
        print("[extract_dinov3] config.json нет после копирования", file=sys.stderr)
        return 1

    print(f"[extract_dinov3] OK: {snap} → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
