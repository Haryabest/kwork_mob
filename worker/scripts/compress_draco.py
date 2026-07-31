"""Draco-сжатие §6 / §9: GLB ≤15 МБ Ozon / ≤20 МБ WB (gltf-transform / gltfpack / cascade)."""

from __future__ import annotations

import io
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from marketplace_limits import max_bytes, normalize_marketplace, size_status


def _load_marketplace(root: Path) -> str:
    meta_path = root / "task_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return normalize_marketplace(meta.get("target_marketplace"))
        except Exception:  # noqa: BLE001
            pass
    return normalize_marketplace(os.getenv("TASK_TARGET_MARKETPLACE"))


def _write_result(root: Path, dst: Path, marketplace: str) -> None:
    size = dst.stat().st_size if dst.exists() else 0
    status = size_status(size, marketplace)
    (root / "compress_result.json").write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")


def _glb_has_textures(path: Path) -> bool:
    try:
        data = path.read_bytes()
        if data[:4] != b"glTF":
            return False
        json_len = struct.unpack_from("<I", data, 12)[0]
        chunk = bytes(data[20 : 20 + json_len]).decode("utf-8").rstrip(" \x00")
        gltf = json.loads(chunk)
        return bool(gltf.get("images")) or bool(gltf.get("textures"))
    except Exception:  # noqa: BLE001
        return False


def _try_gltfpack(src: Path, dst: Path) -> bool:
    cmd = shutil.which("gltfpack")
    if not cmd:
        return False
    try:
        r = subprocess.run(
            [cmd, "-i", str(src), "-o", str(dst), "-cc", "-tc"],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0 or not dst.exists():
            err = (r.stderr or r.stdout or "").strip()
            if err:
                print(f"[compress_draco] gltfpack: {err[-400:]}")
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[compress_draco] gltfpack failed: {exc}")
        return False


def _try_pygltf_texture_resize(src: Path, dst: Path, max_side: int, quality: int) -> bool:
    try:
        import base64
        from PIL import Image
        from pygltflib import GLTF2
    except Exception:
        return False
    try:
        gltf = GLTF2().load(str(src))
        if not gltf.images:
            return False
        blob = bytearray(gltf.binary_blob() or b"")
        if not blob and not any(
            img.uri and img.uri.startswith("data:") for img in gltf.images if img.uri
        ):
            return False
        changed = False
        for img_def in gltf.images:
            data = None
            if img_def.uri and img_def.uri.startswith("data:"):
                data = base64.b64decode(img_def.uri.split(",", 1)[-1])
            elif img_def.bufferView is not None and gltf.bufferViews:
                bv = gltf.bufferViews[img_def.bufferView]
                start = bv.byteOffset or 0
                data = bytes(blob[start : start + bv.byteLength])
            if not data:
                continue
            try:
                im = Image.open(io.BytesIO(data))
            except Exception:
                continue
            w, h = im.size
            if max(w, h) <= max_side:
                continue
            scale = max_side / max(w, h)
            im = im.resize(
                (max(1, int(w * scale)), max(1, int(h * scale))),
                Image.Resampling.LANCZOS,
            )
            out_io = io.BytesIO()
            mime = (img_def.mimeType or "").lower()
            if mime in ("image/jpeg", "image/jpg"):
                if im.mode != "RGB":
                    im = im.convert("RGB")
                im.save(out_io, format="JPEG", quality=quality, optimize=True)
                img_def.mimeType = "image/jpeg"
            else:
                if im.mode != "RGBA":
                    im = im.convert("RGBA")
                im.save(out_io, format="PNG", optimize=True)
                img_def.mimeType = "image/png"
            new_data = out_io.getvalue()
            changed = True
            if img_def.uri and img_def.uri.startswith("data:"):
                enc = base64.b64encode(new_data).decode("ascii")
                img_def.uri = f"data:{img_def.mimeType};base64,{enc}"
            elif img_def.bufferView is not None and gltf.bufferViews:
                bv = gltf.bufferViews[img_def.bufferView]
                start = bv.byteOffset or 0
                old_len = bv.byteLength
                if len(new_data) <= old_len:
                    blob[start : start + len(new_data)] = new_data
                    if len(new_data) < old_len:
                        blob[start + len(new_data) : start + old_len] = b"\x00" * (
                            old_len - len(new_data)
                        )
                    bv.byteLength = len(new_data)
                else:
                    pad = (4 - (len(blob) % 4)) % 4
                    if pad:
                        blob.extend(b"\x00" * pad)
                    new_start = len(blob)
                    blob.extend(new_data)
                    bv.byteOffset = new_start
                    bv.byteLength = len(new_data)
                if gltf.buffers:
                    gltf.buffers[0].byteLength = len(blob)
        if not changed:
            return False
        gltf.set_binary_blob(bytes(blob))
        gltf.save(str(dst))
        return dst.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[compress_draco] pygltf resize failed: {exc}")
        return False


def _try_gltf_transform(src: Path, dst: Path, quantize: int) -> bool:
    cmd = shutil.which("gltf-transform")
    if not cmd:
        return False
    try:
        tmp = dst.with_suffix(".draco.glb")
        r = subprocess.run(
            [
                cmd,
                "draco",
                str(src),
                str(tmp),
                "--method",
                "edgebreaker",
                "--quantize-position",
                str(quantize),
                "--quantize-normal",
                str(max(quantize - 2, 6)),
                "--quantize-texcoord",
                str(max(quantize - 2, 8)),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0 or not tmp.exists():
            print(f"[compress_draco] gltf-transform: {r.stderr[-400:]}")
            return False
        shutil.move(str(tmp), str(dst))
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[compress_draco] gltf-transform failed: {exc}")
        return False


def _try_trimesh_simplify(src: Path, dst: Path, face_count: int) -> bool:
    if _glb_has_textures(src):
        print("[compress_draco] skip trimesh simplify — GLB с текстурами (сбросит PBR)")
        return False
    try:
        import trimesh
    except Exception:
        return False
    try:
        mesh = trimesh.load(str(src), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(g for g in mesh.geometry.values()))
        if len(mesh.faces) > face_count:
            mesh = mesh.simplify_quadric_decimation(face_count=face_count)
        mesh.export(str(dst))
        return dst.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[compress_draco] simplify failed: {exc}")
        return False


def _try_gltf_webp(src: Path, dst: Path) -> bool:
    cmd = shutil.which("gltf-transform")
    if not cmd:
        return False
    try:
        tmp = dst.with_suffix(".webp.glb")
        r = subprocess.run(
            [cmd, "webp", str(src), str(tmp)],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0 or not tmp.exists():
            return False
        shutil.move(str(tmp), str(dst))
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[compress_draco] webp failed: {exc}")
        return False


def main(task_dir: str) -> None:
    root = Path(task_dir)
    marketplace = _load_marketplace(root)
    max_limit = max_bytes(marketplace)
    src = root / "watermarked.glb"
    if not src.exists():
        src = root / "pbr.glb"
    dst = root / "model.glb"
    if not src.exists():
        raise SystemExit("missing mesh for compress_draco")

    if os.getenv("WORKER_PIPELINE_MODE", "").lower() == "stub":
        shutil.copy2(src, dst)
        print(f"[compress_draco] stub copy → {dst} ({dst.stat().st_size} bytes)")
        _write_result(root, dst, marketplace)
        return

    src_size = src.stat().st_size
    if src_size <= max_limit and os.getenv("COMPRESS_DRACO_FORCE", "0") not in ("1", "true", "yes"):
        shutil.copy2(src, dst)
        print(f"[compress_draco] under limit, copy as-is → {dst} ({src_size} bytes)")
        _write_result(root, dst, marketplace)
        return

    current = src
    textured = _glb_has_textures(src)
    if textured:
        print(f"[compress_draco] textured GLB ({src_size} bytes) — сохраняем PBR при сжатии")

    if _try_gltfpack(current, dst):
        size = dst.stat().st_size
        print(f"[compress_draco] gltfpack → {size} bytes ({marketplace})")
        if size <= max_limit:
            _write_result(root, dst, marketplace)
            return
        current = dst

    if _try_gltf_webp(current, dst):
        size = dst.stat().st_size
        print(f"[compress_draco] webp textures → {size} bytes ({marketplace})")
        if size <= max_limit:
            _write_result(root, dst, marketplace)
            return
        current = dst

    for max_tex in (2048, 1024, 512):
        if _try_pygltf_texture_resize(current, dst, max_tex, 82):
            size = dst.stat().st_size
            print(f"[compress_draco] pygltf tex {max_tex}px → {size} bytes")
            if size <= max_limit:
                _write_result(root, dst, marketplace)
                return
            current = dst

    for quantize in (14, 12, 10, 8):
        if _try_gltf_transform(current, dst, quantize):
            size = dst.stat().st_size
            print(f"[compress_draco] gltf-transform q={quantize} → {size} bytes ({marketplace})")
            if size <= max_limit:
                _write_result(root, dst, marketplace)
                return
            current = dst
        if _try_gltfpack(current, dst):
            size = dst.stat().st_size
            print(f"[compress_draco] gltfpack → {size} bytes ({marketplace})")
            if size <= max_limit:
                _write_result(root, dst, marketplace)
                return
            current = dst

    if textured:
        if not dst.exists() or dst.stat().st_size > max_limit:
            shutil.copy2(src, dst)
            print(
                f"[compress_draco] textured fallback copy → {dst.stat().st_size} bytes "
                "(gltf-transform/sharp сломан — пересоберите worker)"
            )
    else:
        for faces in (30000, 15000, 8000, 4000):
            if dst.exists() and dst.stat().st_size <= max_limit:
                _write_result(root, dst, marketplace)
                return
            if _try_trimesh_simplify(current, dst, faces):
                size = dst.stat().st_size
                print(f"[compress_draco] simplify faces={faces} → {size} bytes")
                if size <= max_limit:
                    _write_result(root, dst, marketplace)
                    return
                current = dst

    if not dst.exists():
        shutil.copy2(src, dst)
    size = dst.stat().st_size
    status = size_status(size, marketplace)
    print(f"[compress_draco] final → {dst} ({size} bytes, limit={max_limit}, mp={marketplace})")
    _write_result(root, dst, marketplace)
    if status["hard_limit_exceeded"]:
        if os.getenv("COMPRESS_ALLOW_OVER_LIMIT", "0").lower() in ("1", "true", "yes"):
            print(
                f"[compress_draco] over limit ({size} > {max_limit}), "
                "COMPRESS_ALLOW_OVER_LIMIT=1 — продолжаем с флагом"
            )
            return
        raise SystemExit(f"GLB > hard limit after cascade: {size}")
    if status["warning_size_exceeded"]:
        print("[compress_draco] warning_size_exceeded — сохраняем с флагом §6.6.3")


if __name__ == "__main__":
    main(sys.argv[1])
