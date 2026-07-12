"""Апсейл real_scale: размеры в extras GLB (§17)."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path


def _read_glb_json(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError("not glb")
    json_len = struct.unpack_from("<I", data, 12)[0]
    json_start = 20
    chunk = data[json_start : json_start + json_len]
    gltf = json.loads(chunk.decode("utf-8").rstrip("\x00"))
    return gltf, data


def _write_glb(path: Path, gltf: dict, bin_blob: bytes | None = None) -> None:
    # упрощённо: если есть bin chunk — сохраняем; иначе только JSON (stub)
    raw = path.read_bytes()
    if len(raw) < 20:
        path.write_text(json.dumps(gltf), encoding="utf-8")
        return
    json_len = struct.unpack_from("<I", raw, 12)[0]
    json_start = 20
    rest = raw[json_start + json_len :]
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    out = bytearray()
    out += b"glTF"
    out += struct.pack("<II", 2, 0)  # length filled later
    out += struct.pack("<I", len(json_bytes))
    out += b"JSON"
    out += json_bytes
    out += rest if rest else (bin_blob or b"")
    total = len(out)
    struct.pack_into("<I", out, 8, total)
    path.write_bytes(bytes(out))


def main(task_dir: Path) -> None:
    meta = {}
    meta_path = task_dir / "task_meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    cal = meta.get("scale_calibration") or {}
    w = float(cal.get("width") or cal.get("w") or 0.3)
    h = float(cal.get("height") or cal.get("h") or 0.5)
    d = float(cal.get("depth") or cal.get("d") or 0.2)
    glb = task_dir / "model.glb"
    if not glb.exists():
        raise SystemExit("model.glb missing")
    try:
        gltf, _ = _read_glb_json(glb)
        extras = gltf.setdefault("extras", {})
        extras["real_scale"] = {"width": w, "height": h, "depth": d, "unit": "m"}
        _write_glb(glb, gltf)
    except Exception:
        # fallback sidecar
        (task_dir / "real_scale.json").write_text(
            json.dumps({"width": w, "height": h, "depth": d, "unit": "m"}),
            encoding="utf-8",
        )
    print(f"real_scale applied {w}x{h}x{d}m")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
