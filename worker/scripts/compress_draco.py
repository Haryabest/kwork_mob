"""Draco-сжатие §6 / §9: GLB ≤15 МБ (gltf-transform / gltfpack / cascade)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

MAX_BYTES = int(os.getenv("GLB_MAX_BYTES", str(15 * 1024 * 1024)))


def _try_gltf_transform(src: Path, dst: Path, quantize: int) -> bool:
    cmd = shutil.which("gltf-transform")
    if not cmd:
        return False
    try:
        tmp = dst.with_suffix(".draco.glb")
        r = subprocess.run(
            [
                cmd,
                "draco",
                str(src),
                str(tmp),
                "--method",
                "edgebreaker",
                "--quantize-position",
                str(quantize),
                "--quantize-normal",
                str(max(quantize - 2, 6)),
                "--quantize-texcoord",
                str(max(quantize - 2, 8)),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0 or not tmp.exists():
            print(f"[compress_draco] gltf-transform: {r.stderr[-400:]}")
            return False
        shutil.move(str(tmp), str(dst))
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[compress_draco] gltf-transform failed: {exc}")
        return False


def _try_gltfpack(src: Path, dst: Path) -> bool:
    cmd = shutil.which("gltfpack")
    if not cmd:
        return False
    try:
        r = subprocess.run(
            [cmd, "-i", str(src), "-o", str(dst), "-cc", "-tc"],
            capture_output=True,
            text=True,
            check=False,
        )
        return r.returncode == 0 and dst.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[compress_draco] gltfpack failed: {exc}")
        return False


def _try_trimesh_simplify(src: Path, dst: Path, face_count: int) -> bool:
    try:
        import trimesh
    except Exception:
        return False
    try:
        mesh = trimesh.load(str(src), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(g for g in mesh.geometry.values()))
        if len(mesh.faces) > face_count:
            mesh = mesh.simplify_quadric_decimation(face_count=face_count)
        mesh.export(str(dst))
        return dst.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[compress_draco] simplify failed: {exc}")
        return False


def main(task_dir: str) -> None:
    root = Path(task_dir)
    src = root / "watermarked.glb"
    if not src.exists():
        src = root / "pbr.glb"
    dst = root / "model.glb"
    if not src.exists():
        raise SystemExit("missing mesh for compress_draco")

    current = src
    # каскад: Draco → сильнее quantize → simplify faces
    for quantize in (14, 12, 10, 8):
        if _try_gltf_transform(current, dst, quantize):
            size = dst.stat().st_size
            print(f"[compress_draco] gltf-transform q={quantize} → {size} bytes")
            if size <= MAX_BYTES:
                return
            current = dst
        elif _try_gltfpack(current, dst):
            size = dst.stat().st_size
            print(f"[compress_draco] gltfpack → {size} bytes")
            if size <= MAX_BYTES:
                return
            current = dst
            break
        else:
            break

    for faces in (30000, 15000, 8000, 4000):
        if dst.exists() and dst.stat().st_size <= MAX_BYTES:
            return
        if _try_trimesh_simplify(current, dst, faces):
            size = dst.stat().st_size
            print(f"[compress_draco] simplify faces={faces} → {size} bytes")
            if size <= MAX_BYTES:
                return
            current = dst

    if not dst.exists():
        shutil.copy2(src, dst)
    size = dst.stat().st_size
    print(f"[compress_draco] final → {dst} ({size} bytes, limit={MAX_BYTES})")
    if size > MAX_BYTES:
        raise SystemExit(f"GLB still >15MB after cascade: {size}")


if __name__ == "__main__":
    main(sys.argv[1])
