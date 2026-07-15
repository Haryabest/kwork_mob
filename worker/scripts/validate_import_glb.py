"""Import GLB validation: GLB 2.0, PBR, size gate §6.10 (без watermark.hmac)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

MAX_BYTES = 50 * 1024 * 1024
DRACO_THRESHOLD = 15 * 1024 * 1024
MARKETPLACE_LIMIT = 15 * 1024 * 1024


def _read_glb(path: Path) -> tuple[dict, bytes | None]:
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"glTF":
        raise SystemExit(f"invalid GLB magic: {data[:4]!r}")
    import struct

    chunk0_len = struct.unpack("<I", data[12:16])[0]
    chunk0_type = data[16:20]
    if chunk0_type != b"JSON":
        raise SystemExit("GLB chunk0 must be JSON")
    gltf = json.loads(data[20 : 20 + chunk0_len].decode("utf-8"))
    bin_blob = None
    off = 20 + chunk0_len
    if off + 8 <= len(data):
        bin_len = struct.unpack("<I", data[off : off + 4])[0]
        if data[off + 4 : off + 8] == b"BIN\x00":
            bin_blob = data[off + 8 : off + 8 + bin_len]
    if gltf.get("asset", {}).get("version") != "2.0":
        raise SystemExit("GLB must be glTF 2.0")
    return gltf, bin_blob


def _ensure_pbr_stubs(gltf: dict) -> bool:
    """Добавить PBR-заглушки если материалов нет (§6.10)."""
    changed = False
    if not gltf.get("materials"):
        gltf["materials"] = [
            {
                "name": "import_default",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.8, 0.8, 0.8, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.5,
                },
            }
        ]
        changed = True
    if gltf.get("meshes") and not gltf["meshes"][0].get("primitives"):
        return changed
    if gltf.get("meshes"):
        for mesh in gltf["meshes"]:
            for prim in mesh.get("primitives") or []:
                if "material" not in prim and gltf.get("materials"):
                    prim["material"] = 0
                    changed = True
    return changed


def _write_glb(path: Path, gltf: dict, bin_blob: bytes | None) -> None:
    import struct

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * json_pad
    chunks = bytearray()
    chunks += struct.pack("<I", len(json_bytes))
    chunks += b"JSON"
    chunks += json_bytes
    if bin_blob:
        bin_pad = (4 - len(bin_blob) % 4) % 4
        bin_blob = bin_blob + b"\x00" * bin_pad
        chunks += struct.pack("<I", len(bin_blob))
        chunks += b"BIN\x00"
        chunks += bin_blob
    header = b"glTF" + struct.pack("<II", 2, 12 + len(chunks))
    path.write_bytes(header + chunks)


def _pbr_score(gltf: dict) -> float:
    mats = gltf.get("materials") or []
    if not mats:
        return 0.0
    for mat in mats:
        pbr = mat.get("pbrMetallicRoughness") or mat.get("extensions", {}).get("KHR_materials_pbrSpecularGlossiness")
        if pbr:
            return 1.0
    return 0.5


def main(task_dir: str) -> None:
    root = Path(task_dir)
    raw = root / "model_raw.glb"
    model = root / "model.glb"
    if raw.exists() and not model.exists():
        shutil.copy2(raw, model)
    if not model.exists():
        raise SystemExit("model.glb missing for import validation")

    size = model.stat().st_size
    if size <= 12:
        raise SystemExit(f"model.glb too small: {size}")
    if size > MAX_BYTES:
        raise SystemExit(f"model.glb too large: {size} > {MAX_BYTES}")

    gltf, bin_blob = _read_glb(model)
    changed = _ensure_pbr_stubs(gltf)
    if changed:
        _write_glb(model, gltf, bin_blob)
        size = model.stat().st_size

    pbr_ok = _pbr_score(gltf) >= 0.5
    needs_draco = size > DRACO_THRESHOLD

    report = {
        "pipeline": "import_validate",
        "gltf_version": gltf.get("asset", {}).get("version"),
        "size_bytes": size,
        "pbr_ok": pbr_ok,
        "needs_draco": needs_draco,
        "marketplace_limit_bytes": MARKETPLACE_LIMIT,
        "passed": pbr_ok,
    }
    (root / "import_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "pbr_ok.flag").write_text("1" if pbr_ok else "0", encoding="utf-8")
    print(
        f"[validate_import_glb] ok size={size} pbr={pbr_ok} needs_draco={needs_draco}"
    )
    if not pbr_ok:
        raise SystemExit("import_pbr_validation_failed")


if __name__ == "__main__":
    main(sys.argv[1])
