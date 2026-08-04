"""Hole filling §17: зашивка дыр в меше (trimesh / Open3D)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


def _fill_trimesh(src: Path, dst: Path) -> bool:
    try:
        import trimesh
    except Exception:
        return False
    try:
        loaded = trimesh.load(str(src), force="scene")
        if isinstance(loaded, trimesh.Scene):
            geoms = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if not geoms:
                return False
            mesh = trimesh.util.concatenate(geoms) if len(geoms) > 1 else geoms[0]
        elif isinstance(loaded, trimesh.Trimesh):
            mesh = loaded
        else:
            return False

        mesh.remove_duplicate_faces()
        mesh.remove_degenerate_faces()
        mesh.remove_unreferenced_vertices()
        try:
            mesh.merge_vertices()
        except Exception:  # noqa: BLE001
            pass

        # Несколько проходов: мелкие дыры + broken topology
        iters = max(1, int(os.getenv("TRELLIS2_HOLE_ITERATIONS", "5")))
        for _ in range(iters):
            try:
                mesh.fill_holes()
            except Exception:  # noqa: BLE001
                break
            try:
                trimesh.repair.fix_normals(mesh)
                trimesh.repair.fix_winding(mesh)
            except Exception:  # noqa: BLE001
                pass

        # Broken faces / inverted normals
        try:
            trimesh.repair.broken_faces(mesh, color=None)
        except Exception:  # noqa: BLE001
            pass
        try:
            if not mesh.is_watertight and hasattr(trimesh.repair, "fill_holes"):
                trimesh.repair.fill_holes(mesh)
        except Exception:  # noqa: BLE001
            pass

        # Убрать крошечные floating islands
        try:
            components = mesh.split(only_watertight=False)
            if len(components) > 1:
                components = sorted(components, key=lambda m: len(m.faces), reverse=True)
                keep = [components[0]]
                main_area = float(components[0].area) if components[0].area else 1.0
                for c in components[1:]:
                    if c.area and (c.area / main_area) >= 0.02:
                        keep.append(c)
                mesh = trimesh.util.concatenate(keep) if len(keep) > 1 else keep[0]
        except Exception:  # noqa: BLE001
            pass

        mesh.export(str(dst))
        ok = dst.exists() and dst.stat().st_size > 500
        if ok:
            print(
                f"[hole_filling] trimesh faces={len(mesh.faces)} "
                f"watertight={getattr(mesh, 'is_watertight', None)} → {dst.name}"
            )
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"[hole_filling] trimesh failed: {exc}")
        return False


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
        mesh.remove_duplicated_triangles()
        mesh.remove_degenerate_triangles()
        mesh.remove_non_manifold_edges()
        if hasattr(mesh, "fill_holes"):
            mesh.fill_holes()
        else:
            mesh = mesh.filter_smooth_taubin(number_of_iterations=5)
        mesh.compute_vertex_normals()
        return bool(o3d.io.write_triangle_mesh(str(dst), mesh)) and dst.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[hole_filling] open3d failed: {exc}")
        return False


def main(task_dir: str) -> None:
    root = Path(task_dir)
    src = root / "retopo.glb"
    if not src.exists():
        src = root / "raw_mesh.glb"
    if not src.exists():
        raise SystemExit("mesh missing for hole_filling")
    dst = root / "retopo.glb"
    tmp = root / "retopo_filled.glb"
    ok = _fill_trimesh(src, tmp) or _fill_open3d(src, tmp)
    if ok:
        shutil.move(str(tmp), dst)
        method = "mesh_fill"
    else:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
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
