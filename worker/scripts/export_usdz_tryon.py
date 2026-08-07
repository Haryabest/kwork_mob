"""USDZ для Wildberries / iOS AR Quick Look (GLB → USDZ)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def _glb_source(root: Path) -> Path:
    for name in ("model.glb", "retopo.glb", "raw_mesh.glb"):
        p = root / name
        if p.exists() and p.stat().st_size > 500:
            return p
    raise SystemExit("GLB missing for USDZ export")


def _blender_usdz(glb: Path, usdz: Path) -> bool:
    blender = os.getenv("BLENDER_BIN") or shutil.which("blender")
    if not blender:
        return False
    usdz.parent.mkdir(parents=True, exist_ok=True)
    if usdz.exists():
        usdz.unlink()
    script = f"""
import bpy
import sys

glb = {str(glb)!r}
usdz = {str(usdz)!r}

bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    bpy.ops.import_scene.gltf(filepath=glb)
except Exception as exc:
    print(f"import_scene.gltf failed: {{exc}}", file=sys.stderr)
    sys.exit(1)

if not bpy.context.scene.objects:
    print("no objects after gltf import", file=sys.stderr)
    sys.exit(2)

kwargs = {{
    "filepath": usdz,
    "export_textures": True,
    "relative_paths": True,
}}
try:
    kwargs["generate_preview_surface"] = True
    bpy.ops.wm.usd_export(**kwargs)
except TypeError:
    kwargs.pop("generate_preview_surface", None)
    bpy.ops.wm.usd_export(**kwargs)
except Exception as exc:
    print(f"usd_export failed: {{exc}}", file=sys.stderr)
    sys.exit(3)

if not Path(usdz).exists() or Path(usdz).stat().st_size < 100:
    print("usdz file empty or missing", file=sys.stderr)
    sys.exit(4)
print("blender_usdz_ok")
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(script)
        py_path = tf.name
    try:
        r = subprocess.run(
            [blender, "-b", "--python", py_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=int(os.getenv("USDZ_EXPORT_TIMEOUT_SEC", "300")),
        )
        if r.returncode != 0:
            tail = (r.stderr or r.stdout or "")[-600:]
            print(f"[export_usdz] blender rc={r.returncode}: {tail}")
            return False
        ok = usdz.exists() and usdz.stat().st_size > 100
        if ok:
            print(f"[export_usdz] blender → {usdz.name} ({usdz.stat().st_size} bytes)")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"[export_usdz] blender failed: {exc}")
        return False
    finally:
        Path(py_path).unlink(missing_ok=True)


def _try_usd_from_gltf(glb: Path, usdz: Path) -> bool:
    cmd = shutil.which("usd_from_gltf")
    if not cmd:
        return False
    try:
        out_dir = usdz.parent / "_usd_tmp"
        out_dir.mkdir(exist_ok=True)
        r = subprocess.run(
            [cmd, str(glb), "-o", str(out_dir / "model")],
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        if r.returncode != 0:
            print(f"[export_usdz] usd_from_gltf: {(r.stderr or '')[-400:]}")
            return False
        produced = list(out_dir.glob("**/*.usdz"))
        if produced:
            shutil.copy2(produced[0], usdz)
            shutil.rmtree(out_dir, ignore_errors=True)
            return usdz.stat().st_size > 100
        usdc = list(out_dir.glob("**/*.usdc")) + list(out_dir.glob("**/*.usda"))
        if usdc:
            ok = _pack_usdz_archive(usdc[0], glb, usdz)
            shutil.rmtree(out_dir, ignore_errors=True)
            return ok
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"[export_usdz] usd_from_gltf failed: {exc}")
        return False


def _pack_usdz_archive(usd_file: Path, glb: Path, usdz: Path) -> bool:
    """Zip USD + textures/GLB без compression (Apple USDZ)."""
    try:
        if usdz.exists():
            usdz.unlink()
        with zipfile.ZipFile(usdz, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.write(usd_file, usd_file.name)
            if glb.exists():
                zf.write(glb, glb.name)
        return usdz.exists() and usdz.stat().st_size > 100
    except Exception as exc:  # noqa: BLE001
        print(f"[export_usdz] pack failed: {exc}")
        return False


def export_usdz(glb: Path, usdz: Path) -> str:
    usdz.parent.mkdir(parents=True, exist_ok=True)
    if usdz.exists():
        usdz.unlink()
    for name, fn in (
        ("blender", _blender_usdz),
        ("usd_from_gltf", _try_usd_from_gltf),
    ):
        if fn(glb, usdz):
            return name
    raise RuntimeError("USDZ export failed (blender/usd_from_gltf)")


def main(task_dir: str) -> None:
    root = Path(task_dir)
    glb = _glb_source(root)
    usdz = root / "model.usdz"
    method = export_usdz(glb, usdz)
    meta_path = root / "task_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta["usdz_export"] = {"method": method, "bytes": usdz.stat().st_size}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[export_usdz] {method} → {usdz} ({usdz.stat().st_size} bytes)")


if __name__ == "__main__":
    main(sys.argv[1])
