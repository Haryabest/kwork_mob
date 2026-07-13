"""Bake PBR §6.4: Blender high→low NORMAL + roughness/metallic по категории.

Порядок: Blender headless (bake_pbr_blender.py) → procedural trimesh fallback.
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Категория → (roughness, metallic) по ТЗ §6.4.2
CATEGORY_PBR = {
    "electronics": (0.30, 0.85),
    "clothing": (0.80, 0.05),
    "shoes": (0.65, 0.10),
    "furniture": (0.60, 0.00),
    "decor": (0.55, 0.05),
    "toys": (0.50, 0.05),
    "adult": (0.55, 0.10),
    "other": (0.55, 0.05),
}


def _load_category(root: Path) -> str:
    meta = root / "task_meta.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            cat = (data.get("category") or data.get("product_category") or "other").strip().lower()
            return cat if cat in CATEGORY_PBR else "other"
        except Exception:  # noqa: BLE001
            pass
    return (os.getenv("TASK_CATEGORY") or "other").strip().lower()


def _blender_bake(root: Path, high: Path, low: Path, maps_dir: Path, category: str) -> bool:
    blender = os.getenv("BLENDER_BIN") or shutil.which("blender")
    if not blender:
        return False
    script = Path(__file__).resolve().parent / "bake_pbr_blender.py"
    if not script.exists():
        return False
    maps_dir.mkdir(parents=True, exist_ok=True)
    size = int(os.getenv("PBR_MAP_SIZE", "1024"))
    cmd = [
        blender,
        "-b",
        "-P",
        str(script),
        "--",
        "--highpoly",
        str(high),
        "--lowpoly",
        str(low),
        "--outdir",
        str(maps_dir),
        "--category",
        category,
        "--size",
        str(size),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=900)
        ok = (maps_dir / "normal.png").exists() and (maps_dir / "roughness.png").exists()
        if not ok:
            print(f"[bake_pbr] blender rc={r.returncode}: {(r.stderr or r.stdout)[-800:]}")
        else:
            print(f"[bake_pbr] blender maps → {maps_dir}")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"[bake_pbr] blender failed: {exc}")
        return False


def _procedural_maps(maps_dir: Path, category: str) -> tuple[float, float]:
    maps_dir.mkdir(parents=True, exist_ok=True)
    size = int(os.getenv("PBR_MAP_SIZE", "512"))
    roughness, metallic = CATEGORY_PBR.get(category, CATEGORY_PBR["other"])
    if os.getenv("PBR_ROUGHNESS"):
        roughness = float(os.getenv("PBR_ROUGHNESS", str(roughness)))
    if os.getenv("PBR_METALLIC"):
        metallic = float(os.getenv("PBR_METALLIC", str(metallic)))

    normal = np.zeros((size, size, 3), dtype=np.uint8)
    normal[:, :] = (128, 128, 255)
    Image.fromarray(normal, "RGB").save(maps_dir / "normal.png")
    Image.fromarray(
        np.full((size, size), int(max(0, min(1, roughness)) * 255), dtype=np.uint8), "L"
    ).save(maps_dir / "roughness.png")
    Image.fromarray(
        np.full((size, size), int(max(0, min(1, metallic)) * 255), dtype=np.uint8), "L"
    ).save(maps_dir / "metallic.png")
    return roughness, metallic


def _bake_trimesh(src: Path, dst: Path, maps_dir: Path, roughness: float, metallic: float) -> bool:
    try:
        import trimesh
        from trimesh.visual.material import PBRMaterial
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
        _ = mesh.vertex_normals
        try:
            mat = PBRMaterial(
                name="baked_pbr",
                roughnessFactor=roughness,
                metallicFactor=metallic,
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
            "roughness": roughness,
            "metallic": metallic,
            "faces": int(len(mesh.faces)),
        }
        (src.parent / "pbr_meta.json").write_text(json.dumps(meta), encoding="utf-8")
        print(f"[bake_pbr] trimesh → {dst} faces={len(mesh.faces)}")
        return dst.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[bake_pbr] failed: {exc}")
        return False


def _inject_pbr_extras(glb_path: Path, roughness: float, metallic: float) -> None:
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
        extras["pbr"] = {"roughness": roughness, "metallic": metallic}
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
    high = root / "raw_mesh.glb"
    low = root / "retopo.glb"
    if not low.exists():
        low = high if high.exists() else None
    if low is None or not low.exists():
        raise SystemExit("missing mesh for bake_pbr")
    if not high.exists():
        high = low

    dst = root / "pbr.glb"
    maps_dir = root / "pbr_maps"
    category = _load_category(root)
    roughness, metallic = CATEGORY_PBR.get(category, CATEGORY_PBR["other"])

    baked = _blender_bake(root, high, low, maps_dir, category)
    if not baked:
        roughness, metallic = _procedural_maps(maps_dir, category)
        print(f"[bake_pbr] procedural maps category={category}")
    else:
        # прочитать bake_meta если есть
        meta_txt = maps_dir / "bake_meta.txt"
        if meta_txt.exists():
            for line in meta_txt.read_text(encoding="utf-8").splitlines():
                if line.startswith("roughness="):
                    roughness = float(line.split("=", 1)[1])
                elif line.startswith("metallic="):
                    metallic = float(line.split("=", 1)[1])

    if not _bake_trimesh(low, dst, maps_dir, roughness, metallic):
        dst.write_bytes(low.read_bytes())
        print(f"[bake_pbr] copy fallback → {dst}")
    _inject_pbr_extras(dst, roughness, metallic)


if __name__ == "__main__":
    main(sys.argv[1])
