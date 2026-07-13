"""Ретопология §6.3: Instant Meshes / Quadriflow → Open3D / trimesh fallback.

Целевой polycount по ТЗ: 100k–300k (env RETOPO_TARGET_FACES, default 150000).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _target_faces() -> int:
    # ТЗ §6.3: 100k–300k; премиум 200k–250k
    return int(os.getenv("RETOPO_TARGET_FACES", "150000"))


def _engine() -> str:
    return (os.getenv("RETOPO_ENGINE") or "instant_meshes").strip().lower()


def _glb_to_obj(src: Path, obj: Path) -> bool:
    try:
        import trimesh
    except Exception as exc:  # noqa: BLE001
        print(f"[retopology] trimesh for convert: {exc}")
        return False
    try:
        mesh = trimesh.load(str(src), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        mesh.export(str(obj))
        return obj.exists() and obj.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001
        print(f"[retopology] glb→obj failed: {exc}")
        return False


def _obj_to_glb(obj: Path, dst: Path) -> bool:
    try:
        import trimesh
    except Exception:
        return False
    try:
        mesh = trimesh.load(str(obj), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        mesh.export(str(dst))
        return dst.exists() and dst.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001
        print(f"[retopology] obj→glb failed: {exc}")
        return False


def _retopo_instant_meshes(src: Path, dst: Path, target_faces: int) -> bool:
    """Instant Meshes CLI (§6.3 / §5): /usr/local/bin/instant_meshes."""
    bin_path = os.getenv("INSTANT_MESHES_BIN") or shutil.which("instant_meshes")
    if not bin_path:
        return False
    with tempfile.TemporaryDirectory(prefix="retopo_im_") as tmp:
        tdir = Path(tmp)
        obj_in = tdir / "in.obj"
        obj_out = tdir / "out.obj"
        if not _glb_to_obj(src, obj_in):
            return False
        # Instant Meshes: -f target faces, -o output, deterministic
        cmd = [
            bin_path,
            str(obj_in),
            "-f",
            str(target_faces),
            "-o",
            str(obj_out),
            "-d",  # deterministic
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
            if r.returncode != 0 or not obj_out.exists():
                print(f"[retopology] instant_meshes rc={r.returncode}: {(r.stderr or r.stdout)[-500:]}")
                return False
            ok = _obj_to_glb(obj_out, dst)
            if ok:
                print(f"[retopology] instant_meshes → {dst} target={target_faces}")
            return ok
        except Exception as exc:  # noqa: BLE001
            print(f"[retopology] instant_meshes failed: {exc}")
            return False


def _retopo_quadriflow(src: Path, dst: Path, target_faces: int) -> bool:
    bin_path = os.getenv("QUADRIFLOW_BIN") or shutil.which("quadriflow")
    if not bin_path:
        return False
    with tempfile.TemporaryDirectory(prefix="retopo_qf_") as tmp:
        tdir = Path(tmp)
        obj_in = tdir / "in.obj"
        obj_out = tdir / "out.obj"
        if not _glb_to_obj(src, obj_in):
            return False
        cmd = [bin_path, "-i", str(obj_in), "-o", str(obj_out), "-f", str(max(target_faces // 2, 1000))]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=900)
            if r.returncode != 0 or not obj_out.exists():
                print(f"[retopology] quadriflow rc={r.returncode}: {(r.stderr or '')[-400:]}")
                return False
            ok = _obj_to_glb(obj_out, dst)
            if ok:
                print(f"[retopology] quadriflow → {dst}")
            return ok
        except Exception as exc:  # noqa: BLE001
            print(f"[retopology] quadriflow failed: {exc}")
            return False


def _retopo_open3d(src: Path, dst: Path, target_faces: int) -> bool:
    try:
        import open3d as o3d
    except Exception as exc:  # noqa: BLE001
        print(f"[retopology] open3d unavailable: {exc}")
        return False
    try:
        mesh = o3d.io.read_triangle_mesh(str(src))
        if mesh.is_empty():
            return False
        mesh.remove_duplicated_vertices()
        mesh.remove_duplicated_triangles()
        mesh.remove_degenerate_triangles()
        mesh.remove_non_manifold_edges()
        n = max(len(mesh.triangles), 1)
        if n > target_faces:
            mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=target_faces)
        mesh.compute_vertex_normals()
        ok = o3d.io.write_triangle_mesh(str(dst), mesh, write_triangle_uvs=True)
        print(f"[retopology] open3d faces {n} → {len(mesh.triangles)}")
        return bool(ok) and dst.exists() and dst.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001
        print(f"[retopology] open3d failed: {exc}")
        return False


def _retopo_trimesh(src: Path, dst: Path, target_faces: int) -> bool:
    try:
        import trimesh
    except Exception as exc:  # noqa: BLE001
        print(f"[retopology] trimesh unavailable: {exc}")
        return False
    try:
        mesh = trimesh.load(str(src), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        n = len(mesh.faces)
        if n > target_faces:
            mesh = mesh.simplify_quadric_decimation(face_count=target_faces)
        mesh.export(str(dst))
        print(f"[retopology] trimesh faces {n} → {len(mesh.faces)}")
        return dst.exists() and dst.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001
        print(f"[retopology] trimesh failed: {exc}")
        return False


def main(task_dir: str) -> None:
    root = Path(task_dir)
    src = root / "raw_mesh.glb"
    dst = root / "retopo.glb"
    if not src.exists():
        raise SystemExit(f"missing {src}")

    from pipeline_env import is_stub_pipeline, is_trellis2

    if is_stub_pipeline() or is_trellis2():
        shutil.copy2(src, dst)
        tag = "stub" if is_stub_pipeline() else "trellis2"
        print(f"[retopology] {tag} copy {src.name} → {dst.name} ({dst.stat().st_size} bytes)")
        return

    target = _target_faces()
    engine = _engine()

    order: list = []
    if engine == "quadriflow":
        order = [_retopo_quadriflow, _retopo_instant_meshes, _retopo_open3d, _retopo_trimesh]
    elif engine == "open3d":
        order = [_retopo_open3d, _retopo_trimesh]
    else:
        # default: Instant Meshes по ТЗ
        order = [_retopo_instant_meshes, _retopo_quadriflow, _retopo_open3d, _retopo_trimesh]

    for fn in order:
        if fn(src, dst, target):
            return

    shutil.copy2(src, dst)
    print(f"[retopology] fallback copy {src.name} → {dst.name}")


if __name__ == "__main__":
    main(sys.argv[1])
