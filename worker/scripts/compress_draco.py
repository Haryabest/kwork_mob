"""Draco-сжатие §6 / §9: GLB ≤15 МБ Ozon / ≤20 МБ WB (gltf-transform / gltfpack / cascade)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from marketplace_limits import max_bytes, normalize_marketplace, size_status


def _load_marketplace(root: Path) -> str:
    meta_path = root / "task_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return normalize_marketplace(meta.get("target_marketplace"))
        except Exception:  # noqa: BLE001
            pass
    return normalize_marketplace(os.getenv("TASK_TARGET_MARKETPLACE"))


def _write_result(root: Path, dst: Path, marketplace: str) -> None:
    size = dst.stat().st_size if dst.exists() else 0
    status = size_status(size, marketplace)
    (root / "compress_result.json").write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")


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
    marketplace = _load_marketplace(root)
    max_limit = max_bytes(marketplace)
    src = root / "watermarked.glb"
    if not src.exists():
        src = root / "pbr.glb"
    dst = root / "model.glb"
    if not src.exists():
        raise SystemExit("missing mesh for compress_draco")

    if os.getenv("WORKER_PIPELINE_MODE", "").lower() == "stub":
        shutil.copy2(src, dst)
        print(f"[compress_draco] stub copy → {dst} ({dst.stat().st_size} bytes)")
        _write_result(root, dst, marketplace)
        return

    current = src
    for quantize in (14, 12, 10, 8):
        if _try_gltf_transform(current, dst, quantize):
            size = dst.stat().st_size
            print(f"[compress_draco] gltf-transform q={quantize} → {size} bytes ({marketplace})")
            if size <= max_limit:
                _write_result(root, dst, marketplace)
                return
            current = dst
        elif _try_gltfpack(current, dst):
            size = dst.stat().st_size
            print(f"[compress_draco] gltfpack → {size} bytes ({marketplace})")
            if size <= max_limit:
                _write_result(root, dst, marketplace)
                return
            current = dst
            break
        else:
            break

    for faces in (30000, 15000, 8000, 4000):
        if dst.exists() and dst.stat().st_size <= max_limit:
            _write_result(root, dst, marketplace)
            return
        if _try_trimesh_simplify(current, dst, faces):
            size = dst.stat().st_size
            print(f"[compress_draco] simplify faces={faces} → {size} bytes")
            if size <= max_limit:
                _write_result(root, dst, marketplace)
                return
            current = dst

    if not dst.exists():
        shutil.copy2(src, dst)
    size = dst.stat().st_size
    status = size_status(size, marketplace)
    print(f"[compress_draco] final → {dst} ({size} bytes, limit={max_limit}, mp={marketplace})")
    _write_result(root, dst, marketplace)
    if status["hard_limit_exceeded"]:
        raise SystemExit(f"GLB > hard limit after cascade: {size}")
    if status["warning_size_exceeded"]:
        print("[compress_draco] warning_size_exceeded — сохраняем с флагом §6.6.3")


if __name__ == "__main__":
    main(sys.argv[1])
