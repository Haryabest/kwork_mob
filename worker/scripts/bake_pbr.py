"""Bake PBR §6: normals + roughness/metallic в GLB materials."""

from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def _bake_trimesh(src: Path, dst: Path) -> bool:
    try:
        import trimesh
    except Exception as exc:  # noqa: BLE001
        print(f"[bake_pbr] trimesh unavailable: {exc}")
        return False
    try:
        mesh = trimesh.load(str(src), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            geoms = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
            mesh = trimesh.util.concatenate(geoms) if geoms else None
        if mesh is None or not isinstance(mesh, trimesh.Trimesh):
            return False
        mesh.vertex_normals  # force compute
        # procedural PBR maps 512
        size = int(os.getenv("PBR_MAP_SIZE", "512"))
        normal = np.zeros((size, size, 3), dtype=np.uint8)
        normal[:, :] = (128, 128, 255)  # flat normal
        roughness = np.full((size, size), int(float(os.getenv("PBR_ROUGHNESS", "0.55")) * 255), dtype=np.uint8)
        metallic = np.full((size, size), int(float(os.getenv("PBR_METALLIC", "0.05")) * 255), dtype=np.uint8)

        maps_dir = src.parent / "pbr_maps"
        maps_dir.mkdir(exist_ok=True)
        Image.fromarray(normal, "RGB").save(maps_dir / "normal.png")
        Image.fromarray(roughness, "L").save(maps_dir / "roughness.png")
        Image.fromarray(metallic, "L").save(maps_dir / "metallic.png")

        # material extras
        if not hasattr(mesh.visual, "material") or mesh.visual.material is None:
            mesh.visual = trimesh.visual.TextureVisuals()
        try:
            from trimesh.visual.material import PBRMaterial

            mat = PBRMaterial(
                name="baked_pbr",
                roughnessFactor=float(os.getenv("PBR_ROUGHNESS", "0.55")),
                metallicFactor=float(os.getenv("PBR_METALLIC", "0.05")),
                baseColorFactor=[0.85, 0.85, 0.85, 1.0],
            )
            mesh.visual.material = mat
        except Exception:  # noqa: BLE001
            pass

        mesh.export(str(dst))
        meta = {
            "normal_map": str(maps_dir / "normal.png"),
            "roughness_map": str(maps_dir / "roughness.png"),
            "metallic_map": str(maps_dir / "metallic.png"),
            "faces": int(len(mesh.faces)),
        }
        (src.parent / "pbr_meta.json").write_text(json.dumps(meta), encoding="utf-8")
        print(f"[bake_pbr] trimesh → {dst} faces={len(mesh.faces)}")
        return dst.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[bake_pbr] failed: {exc}")
        return False


def _inject_pbr_extras(glb_path: Path) -> None:
    """Дописывает extras.pbr в glTF JSON chunk."""
    try:
        data = bytearray(glb_path.read_bytes())
        if data[:4] != b"glTF":
            return
        json_len = struct.unpack_from("<I", data, 12)[0]
        json_start = 20
        chunk = bytes(data[json_start : json_start + json_len]).decode("utf-8").rstrip(" \x00")
        gltf = json.loads(chunk)
        extras = gltf.setdefault("extras", {})
        extras["pbr_baked"] = True
        extras["pbr"] = {
            "roughness": float(os.getenv("PBR_ROUGHNESS", "0.55")),
            "metallic": float(os.getenv("PBR_METALLIC", "0.05")),
        }
        new_json = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        while len(new_json) % 4:
            new_json += b" "
        rest = bytes(data[json_start + json_len :])
        out = bytearray()
        out += b"glTF"
        out += struct.pack("<II", 2, 0)
        out += struct.pack("<I", len(new_json))
        out += b"JSON"
        out += new_json
        out += rest
        struct.pack_into("<I", out, 8, len(out))
        glb_path.write_bytes(bytes(out))
    except Exception as exc:  # noqa: BLE001
        print(f"[bake_pbr] extras inject skipped: {exc}")


def main(task_dir: str) -> None:
    root = Path(task_dir)
    src = root / "retopo.glb"
    if not src.exists():
        src = root / "raw_mesh.glb"
    dst = root / "pbr.glb"
    if not src.exists():
        raise SystemExit("missing mesh for bake_pbr")
    if not _bake_trimesh(src, dst):
        dst.write_bytes(src.read_bytes())
        print(f"[bake_pbr] copy fallback → {dst}")
    _inject_pbr_extras(dst)


if __name__ == "__main__":
    main(sys.argv[1])
