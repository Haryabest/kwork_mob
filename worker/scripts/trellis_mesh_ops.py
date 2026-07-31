"""ComfyUI mesh ops: reorient, fill holes, smooth normals."""

from __future__ import annotations

import math
import os


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")


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


def fill_mesh_holes(mesh, *, iterations: int | None = None) -> int:
    if not _env_bool("TRELLIS2_FILL_HOLES", "1"):
        return 0
    iters = iterations if iterations is not None else max(
        1, int(os.getenv("TRELLIS2_HOLE_ITERATIONS", "1"))
    )
    if not hasattr(mesh, "fill_holes"):
        return 0
    filled = 0
    for _ in range(iters):
        try:
            mesh.fill_holes()
            filled += 1
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower() or "cuda error" in str(exc).lower():
                break
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
    meta = {
        "reorient_deg": (os.getenv("TRELLIS2_REORIENT_VERTICES") or "0").strip(),
        "holes_filled_passes": 0,
        "smooth_normals": False,
    }
    reorient_mesh(mesh)
    meta["holes_filled_passes"] = fill_mesh_holes(mesh)
    meta["smooth_normals"] = smooth_mesh_normals(mesh)
    return meta
