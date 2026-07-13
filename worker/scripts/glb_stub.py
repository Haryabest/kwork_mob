"""Stub GLB: превью с фото товара (плоскость + подставка) или куб-fallback."""

from __future__ import annotations

import json
import struct
from pathlib import Path

_PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _find_photo(task_dir: Path) -> Path | None:
    photos = task_dir / "photos"
    if not photos.is_dir():
        return None
    candidates: list[Path] = []
    for p in sorted(photos.iterdir()):
        if p.suffix.lower() in _PHOTO_EXTS and p.name.startswith("view_"):
            candidates.append(p)
    if not candidates:
        for p in sorted(photos.iterdir()):
            if p.suffix.lower() in _PHOTO_EXTS:
                candidates.append(p)
    return candidates[0] if candidates else None


def _write_photo_trimesh(path: Path, photo_path: Path) -> bool:
    try:
        import numpy as np
        import trimesh
        from PIL import Image
    except Exception:
        return False
    try:
        img = Image.open(photo_path).convert("RGB")
        w, h = img.size
        if w < 8 or h < 8:
            return False
        aspect = w / h
        max_h = 0.75
        ph = max_h
        pw = max_h * aspect
        if pw > 0.95:
            pw = 0.95
            ph = pw / aspect

        verts = np.array(
            [[-pw / 2, 0, 0], [pw / 2, 0, 0], [pw / 2, ph, 0], [-pw / 2, ph, 0]],
            dtype=np.float64,
        )
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        uvs = np.array([[0, 1], [1, 1], [1, 0], [0, 0]], dtype=np.float64)
        card = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
        card.visual = trimesh.visual.TextureVisuals(uv=uvs, image=img)

        base = trimesh.creation.box(extents=(pw + 0.12, 0.06, 0.18))
        base.apply_translation([0.0, -0.03, 0.09])
        try:
            from trimesh.visual.material import PBRMaterial

            base.visual.material = PBRMaterial(
                baseColorFactor=[0.92, 0.92, 0.94, 1.0],
                metallicFactor=0.05,
                roughnessFactor=0.85,
            )
        except Exception:
            pass

        scene = trimesh.Scene([card, base])
        path.parent.mkdir(parents=True, exist_ok=True)
        scene.export(str(path))
        return path.exists() and path.stat().st_size > 200
    except Exception:
        return False


def _write_box_trimesh(path: Path) -> bool:
    try:
        import trimesh
        from trimesh.visual.material import PBRMaterial
    except Exception:
        return False
    try:
        mesh = trimesh.creation.box(extents=(0.75, 0.75, 0.75))
        mesh.apply_translation([0.0, 0.0, 0.375])
        mat = PBRMaterial(
            name="stub",
            baseColorFactor=[0.35, 0.55, 0.92, 1.0],
            metallicFactor=0.15,
            roughnessFactor=0.65,
        )
        mesh.visual.material = mat
        path.parent.mkdir(parents=True, exist_ok=True)
        mesh.export(str(path))
        return path.exists() and path.stat().st_size > 100
    except Exception:
        return False


def _write_box_manual(path: Path) -> None:
    s = 0.3
    verts = [
        (-s, -s, -s),
        (s, -s, -s),
        (s, s, -s),
        (-s, s, -s),
        (-s, -s, s),
        (s, -s, s),
        (s, s, s),
        (-s, s, s),
    ]
    positions = struct.pack(f"<{len(verts) * 3}f", *(c for v in verts for c in v))
    faces = [
        0, 1, 2, 0, 2, 3,
        4, 6, 5, 4, 7, 6,
        0, 4, 5, 0, 5, 1,
        2, 6, 7, 2, 7, 3,
        0, 3, 7, 0, 7, 4,
        1, 5, 6, 1, 6, 2,
    ]
    indices = struct.pack(f"<{len(faces)}H", *faces)
    bin_blob = positions + indices
    while len(bin_blob) % 4:
        bin_blob += b"\x00"

    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    gltf = {
        "asset": {"version": "2.0", "generator": "kwork-stub"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.35, 0.55, 0.92, 1.0],
                    "metallicFactor": 0.15,
                    "roughnessFactor": 0.65,
                },
                "doubleSided": True,
            }
        ],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "indices": 1,
                        "mode": 4,
                        "material": 0,
                    }
                ]
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 8,
                "type": "VEC3",
                "max": [max(xs), max(ys), max(zs)],
                "min": [min(xs), min(ys), min(zs)],
            },
            {
                "bufferView": 1,
                "componentType": 5123,
                "count": len(faces),
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions), "target": 34962},
            {"buffer": 0, "byteOffset": len(positions), "byteLength": len(indices), "target": 34963},
        ],
        "buffers": [{"byteLength": len(bin_blob)}],
    }
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "

    chunks = b""
    chunks += struct.pack("<I", len(json_bytes))
    chunks += struct.pack("<I", 0x4E4F534A)
    chunks += json_bytes
    chunks += struct.pack("<I", len(bin_blob))
    chunks += struct.pack("<I", 0x004E4942)
    chunks += bin_blob

    header = struct.pack("<4sII", b"glTF", 2, 12 + len(chunks))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + chunks)


def write_minimal_glb(path: Path, task_dir: Path | str | None = None) -> None:
    """Stub: фото товара на 3D-карточке, иначе синий куб."""
    root = Path(task_dir) if task_dir else None
    if root and (photo := _find_photo(root)) and _write_photo_trimesh(path, photo):
        return
    if _write_box_trimesh(path):
        return
    _write_box_manual(path)


def write_photo_preview_glb(path: Path, task_dir: Path | str) -> None:
    write_minimal_glb(path, task_dir)
