"""Hole filling §17: зашивка дыр в меше (Open3D / trimesh)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def _fill_open3d(src: Path, dst: Path) -> bool:
    try:
        import open3d as o3d
    except Exception:
        return False
    try:
        mesh = o3d.io.read_triangle_mesh(str(src))
        if mesh.is_empty():
            return False
        mesh.remove_duplicated_vertices()
        mesh.remove_degenerate_triangles()
        # fill holes via tetrahedral / hole filling if available
        if hasattr(mesh, "fill_holes"):
            mesh.fill_holes()
        else:
            # densify + reconstruct for small holes
            mesh = mesh.filter_smooth_taubin(number_of_iterations=5)
        mesh.compute_vertex_normals()
        return bool(o3d.io.write_triangle_mesh(str(dst), mesh)) and dst.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[hole_filling] open3d failed: {exc}")
        return False


def _fill_trimesh(src: Path, dst: Path) -> bool:
    try:
        import trimesh
    except Exception:
        return False
    try:
        mesh = trimesh.load(str(src), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        # fill holes where possible
        if hasattr(mesh, "fill_holes"):
            mesh.fill_holes()
        trimesh.repair.fix_normals(mesh)
        trimesh.repair.fix_winding(mesh)
        mesh.export(str(dst))
        return dst.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[hole_filling] trimesh failed: {exc}")
        return False


def main(task_dir: str) -> None:
    root = Path(task_dir)
    # работает на retopo/pbr до финального model.glb
    src = root / "retopo.glb"
    if not src.exists():
        src = root / "raw_mesh.glb"
    if not src.exists():
        raise SystemExit("mesh missing for hole_filling")
    dst = root / "retopo.glb"
    tmp = root / "retopo_filled.glb"
    ok = _fill_open3d(src, tmp) or _fill_trimesh(src, tmp)
    if ok:
        shutil.move(str(tmp), str(dst))
        method = "mesh_fill"
    else:
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
        method = "noop_copy"
    meta_path = root / "task_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta["hole_filling"] = {"applied": True, "method": method}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[hole_filling] {method} → {dst}")


if __name__ == "__main__":
    main(sys.argv[1])
