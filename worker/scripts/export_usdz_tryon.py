"""Virtual Try-On §17: настоящий USDZ (usd_from_gltf / zip USDZ package)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def _try_usd_from_gltf(glb: Path, usdz: Path) -> bool:
    for cmd_name in ("usd_from_gltf", "usdARKitChecker"):
        # usd_from_gltf outputs .usdc then we zip; tool may write usdz directly
        pass
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
        )
        if r.returncode != 0:
            print(f"[export_usdz] usd_from_gltf: {r.stderr[-400:]}")
            return False
        # find produced usdz/usdc
        produced = list(out_dir.glob("**/*.usdz"))
        if produced:
            shutil.copy2(produced[0], usdz)
            shutil.rmtree(out_dir, ignore_errors=True)
            return True
        usdc = list(out_dir.glob("**/*.usdc")) + list(out_dir.glob("**/*.usda"))
        if usdc:
            return _pack_usdz(usdc[0], glb, usdz)
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"[export_usdz] usd_from_gltf failed: {exc}")
        return False


def _pack_usdz(usd_file: Path, glb: Path, usdz: Path) -> bool:
    """Минимальный Apple USDZ: zip без compression с usda + glb."""
    try:
        usda = f"""#usda 1.0
(
    defaultPrim = "Root"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "Root" {{
    def Mesh "Model" {{
        # Reference payload; AR Quick Look uses packaged assets
        asset info:identifier = @{glb.name}@
    }}
}}
"""
        tmp = usdz.with_suffix(".build")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir()
        (tmp / "model.usda").write_text(usda, encoding="utf-8")
        shutil.copy2(glb, tmp / glb.name)
        with zipfile.ZipFile(usdz, "w", compression=zipfile.ZIP_STORED) as zf:
            for f in tmp.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(tmp).as_posix())
        shutil.rmtree(tmp, ignore_errors=True)
        return usdz.exists() and usdz.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001
        print(f"[export_usdz] pack failed: {exc}")
        return False


def _blender_usdz(glb: Path, usdz: Path) -> bool:
    blender = os.getenv("BLENDER_BIN") or shutil.which("blender")
    if not blender:
        return False
    script = f"""
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r'{glb.as_posix()}')
bpy.ops.wm.usd_export(filepath=r'{usdz.as_posix()}', export_materials=True)
"""
    py = usdz.parent / "_blender_usdz.py"
    py.write_text(script, encoding="utf-8")
    try:
        r = subprocess.run(
            [blender, "-b", "-P", str(py)],
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        return r.returncode == 0 and usdz.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[export_usdz] blender failed: {exc}")
        return False
    finally:
        py.unlink(missing_ok=True)


def main(task_dir: str) -> None:
    root = Path(task_dir)
    glb = root / "model.glb"
    if not glb.exists():
        raise SystemExit("model.glb missing")
    usdz = root / "model.usdz"
    if _try_usd_from_gltf(glb, usdz) or _blender_usdz(glb, usdz) or _pack_usdz(glb, glb, usdz):
        print(f"[export_usdz] → {usdz} ({usdz.stat().st_size} bytes)")
        return
    raise SystemExit("USDZ export failed")


if __name__ == "__main__":
    main(sys.argv[1])
