"""ComfyUI mesh ops: reorient, fill holes, smooth normals."""

from __future__ import annotations

import logging
import math
import os

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")


def _is_textured_voxel_mesh(mesh) -> bool:
    """MeshWithVoxel после decode_latent: attrs+coords не трогать до to_glb."""
    attrs = getattr(mesh, "attrs", None)
    coords = getattr(mesh, "coords", None)
    if attrs is None or coords is None:
        return False
    try:
        return len(attrs) > 0 and len(coords) > 0
    except TypeError:
        return True


def reorient_mesh(mesh, degrees: float | None = None) -> None:
    deg = degrees
    if deg is None:
        raw = (os.getenv("TRELLIS2_REORIENT_VERTICES") or "0").strip()
        try:
            deg = float(raw)
        except ValueError:
            return
    if not deg:
        return
    verts = getattr(mesh, "vertices", None)
    if verts is None:
        return
    try:
        import torch

        if isinstance(verts, torch.Tensor):
            rad = math.radians(deg)
            c, s = math.cos(rad), math.sin(rad)
            x = verts[:, 0].clone()
            y = verts[:, 1].clone()
            verts[:, 1] = c * y - s * verts[:, 2]
            verts[:, 2] = s * y + c * verts[:, 2]
            return
    except Exception:  # noqa: BLE001
        pass
    try:
        import numpy as np

        v = np.asarray(verts)
        rad = math.radians(deg)
        c, s = math.cos(rad), math.sin(rad)
        y = v[:, 1].copy()
        z = v[:, 2].copy()
        v[:, 1] = c * y - s * z
        v[:, 2] = s * y + c * z
        if hasattr(mesh, "vertices"):
            mesh.vertices[:] = v
    except Exception:  # noqa: BLE001
        pass


def _max_hole_perimeter() -> float:
    """CuMesh fill_holes: stock to_glb = 3e-2 — крупные дыры на 3-фото не закрывает."""
    raw = (os.getenv("TRELLIS2_MAX_HOLE_PERIMETER") or "1.0").strip()
    try:
        return max(0.25, float(raw))
    except ValueError:
        return 1.0


def fill_mesh_holes(mesh, *, iterations: int | None = None) -> int:
    if not _env_bool("TRELLIS2_FILL_HOLES", "1"):
        return 0
    iters = iterations if iterations is not None else max(
        1, int(os.getenv("TRELLIS2_HOLE_ITERATIONS", "8"))
    )
    if not hasattr(mesh, "fill_holes"):
        # MeshWithVoxel из decode_latent не умеет fill_holes — зашивка идёт в to_glb (cumesh patch)
        logger.info("fill_holes unsupported on %s — зашивка на этапе to_glb", type(mesh).__name__)
        return 0
    peri = _max_hole_perimeter()
    # Сначала мелкие, потом крупнее — меньше артефактов на больших петлях.
    stages = sorted({max(3e-2, peri * 0.4), peri, min(2.0, peri * 1.5)})
    filled = 0
    for stage_peri in stages:
        for _ in range(iters):
            try:
                try:
                    mesh.fill_holes(max_hole_perimeter=stage_peri)
                except TypeError:
                    mesh.fill_holes()
                    filled += 1
                    return filled
                filled += 1
            except RuntimeError as exc:
                if "out of memory" in str(exc).lower() or "cuda error" in str(exc).lower():
                    return filled
                break
            except Exception:  # noqa: BLE001
                break
    return filled


def smooth_mesh_normals(mesh) -> bool:
    if not _env_bool("TRELLIS2_SMOOTH_NORMALS", "1"):
        return False
    if hasattr(mesh, "smooth_normals"):
        try:
            mesh.smooth_normals()
            return True
        except Exception:  # noqa: BLE001
            pass
    try:
        import trimesh

        if isinstance(mesh, trimesh.Trimesh):
            trimesh.smoothing.filter_laplacian(mesh, iterations=2)
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def apply_pre_export_ops(mesh) -> dict:
    """Comfy: Voxel→Trimesh (reorient) + Fill Holes + Smooth Normals."""
    textured = _is_textured_voxel_mesh(mesh)
    meta = {
        "textured_voxel": textured,
        "reorient_deg": None,
        "holes_filled_passes": 0,
        "smooth_normals": False,
        "max_hole_perimeter": _max_hole_perimeter(),
    }
    # attrs — voxel volume; fill_holes меняет только vertices/faces → PBR в to_glb сохраняется.
    if textured:
        logger.info(
            "mesh ops: fill_holes on textured voxel (skip reorient); peri=%.3f",
            meta["max_hole_perimeter"],
        )
        meta["holes_filled_passes"] = fill_mesh_holes(mesh)
    else:
        meta["reorient_deg"] = (os.getenv("TRELLIS2_REORIENT_VERTICES") or "0").strip()
        reorient_mesh(mesh)
        meta["holes_filled_passes"] = fill_mesh_holes(mesh)
        meta["smooth_normals"] = smooth_mesh_normals(mesh)
    return meta
