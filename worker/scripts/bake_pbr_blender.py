"""
Blender headless bake PBR (§6.4): NORMAL high→low + roughness/metallic по категории.

Вызов:
  blender -b -P bake_pbr_blender.py -- --highpoly raw.glb --lowpoly retopo.glb \
    --outdir ./pbr_maps --category electronics
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


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


def _parse_args(argv: list[str]) -> argparse.Namespace:
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    p = argparse.ArgumentParser()
    p.add_argument("--highpoly", required=True)
    p.add_argument("--lowpoly", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--category", default="other")
    p.add_argument("--size", type=int, default=1024)
    return p.parse_args(argv)


def _save_solid_png(path: Path, size: int, value: float, channels: int = 1) -> None:
    """Сохранить однотонную карту через bpy (без PIL). value 0..1."""
    import bpy  # type: ignore

    name = path.stem
    img = bpy.data.images.new(name, width=size, height=size, alpha=False)
    v = max(0.0, min(1.0, float(value)))
    if channels == 1:
        pixels = [v, v, v, 1.0] * (size * size)
    else:
        # flat normal: (0.5, 0.5, 1.0)
        pixels = [0.5, 0.5, 1.0, 1.0] * (size * size)
    img.pixels = pixels
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def main() -> None:
    import bpy  # type: ignore

    args = _parse_args(sys.argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    roughness, metallic = CATEGORY_PBR.get(args.category, CATEGORY_PBR["other"])
    size = int(args.size)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=args.highpoly)
    high_objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in high_objs:
        o.name = f"HIGH_{o.name}"

    bpy.ops.import_scene.gltf(filepath=args.lowpoly)
    low_objs = [
        o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith("HIGH_")
    ]
    if not low_objs:
        raise SystemExit("no lowpoly mesh")

    bpy.ops.object.select_all(action="DESELECT")
    for o in low_objs:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        try:
            bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
        except Exception:
            pass
        bpy.ops.object.mode_set(mode="OBJECT")

    normal_img = bpy.data.images.new("BakeNormal", width=size, height=size, alpha=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 8
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = 0.05
    scene.cycles.bake_type = "NORMAL"

    for o in low_objs:
        if not o.data.materials:
            mat = bpy.data.materials.new(name="BakeMat")
            o.data.materials.append(mat)
        mat = o.data.materials[0]
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = normal_img
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        nt.nodes.active = tex

    bpy.ops.object.select_all(action="DESELECT")
    for o in high_objs:
        o.select_set(True)
    for o in low_objs:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o

    normal_path = outdir / "normal.png"
    try:
        bpy.ops.object.bake(type="NORMAL")
        normal_img.filepath_raw = str(normal_path)
        normal_img.file_format = "PNG"
        normal_img.save()
    except Exception as exc:  # noqa: BLE001
        print(f"[bake_pbr_blender] NORMAL bake failed: {exc}")
        _save_solid_png(normal_path, size, 1.0, channels=3)

    _save_solid_png(outdir / "roughness.png", size, roughness, channels=1)
    _save_solid_png(outdir / "metallic.png", size, metallic, channels=1)

    meta = outdir / "bake_meta.txt"
    meta.write_text(
        f"category={args.category}\nroughness={roughness}\nmetallic={metallic}\n",
        encoding="utf-8",
    )
    print(f"[bake_pbr_blender] maps → {outdir}")


if __name__ == "__main__":
    main()
