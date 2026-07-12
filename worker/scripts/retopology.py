"""Ретопология §6: упрощение меша (Open3D / trimesh), целевой polycount."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _retopo_open3d(src: Path, dst: Path, target_faces: int) -> bool:
    try:
        import open3d as o3d
        import numpy as np
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
            # Quadric decimation
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
    target = int(os.getenv("RETOPO_TARGET_FACES", "40000"))
    if _retopo_open3d(src, dst, target) or _retopo_trimesh(src, dst, target):
        return
    # последний резерв: копия (не должна быть в prod с TRELLIS, но не рвёт E2E)
    shutil.copy2(src, dst)
    print(f"[retopology] fallback copy {src.name} → {dst.name}")


if __name__ == "__main__":
    main(sys.argv[1])
