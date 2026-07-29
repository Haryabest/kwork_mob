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


def _weight_file_ok(path: Path) -> bool:
    try:
        return path.is_file() and path.resolve().stat().st_size > 1_000_000
    except OSError:
        return False


def _find_snapshot() -> Path | None:
    for root in _cache_roots():
        hub = root / "hub" / CACHE_NAME / "snapshots"
        if not hub.is_dir():
            continue
        snaps = sorted(hub.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for snap in snaps:
            if (snap / "config.json").is_file() and (
                _weight_file_ok(snap / "model.safetensors")
                or any(_weight_file_ok(p) for p in snap.glob("*.safetensors"))
            ):
                return snap
    return None


def _copy_resolved(src: Path, dst: Path) -> None:
    if src.is_symlink():
        target = src.resolve()
        if target.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, dst)
            return
        if target.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(target, dst)
            return
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=False, ignore_dangling_symlinks=True)


def main() -> int:
    out = Path(os.getenv("DINOV3_OUT", str(DEFAULT_OUT))).expanduser()
    snap = _find_snapshot()
    if snap is None:
        print("[extract_dinov3] не найден в HF-кэше", file=sys.stderr)
        print(f"[extract_dinov3] искали: {CACHE_NAME}", file=sys.stderr)
        for root in _cache_roots():
            print(f"  - {root / 'hub' / CACHE_NAME}", file=sys.stderr)
        return 1

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    for item in snap.iterdir():
        _copy_resolved(item, out / item.name)

    if not (out / "config.json").is_file():
        print("[extract_dinov3] config.json нет после копирования", file=sys.stderr)
        return 1
    if not (
        _weight_file_ok(out / "model.safetensors")
        or any(_weight_file_ok(p) for p in out.glob("*.safetensors"))
    ):
        print("[extract_dinov3] safetensors битые или пустые", file=sys.stderr)
        return 1

    print(f"[extract_dinov3] OK: {snap} → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
