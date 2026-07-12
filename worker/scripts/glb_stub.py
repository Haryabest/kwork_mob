"""Минимальный валидный GLB (треугольник) для stub-пайплайна."""

from __future__ import annotations

import json
import struct
from pathlib import Path


def write_minimal_glb(path: Path) -> None:
    """glTF 2.0 binary с одним треугольником."""
    # 3 VEC3 positions
    positions = struct.pack(
        "<9f",
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
    )
    indices = struct.pack("<3H", 0, 1, 2)

    bin_blob = positions + indices
    # align to 4
    while len(bin_blob) % 4:
        bin_blob += b"\x00"

    gltf = {
        "asset": {"version": "2.0", "generator": "kwork-stub"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "indices": 1,
                        "mode": 4,
                    }
                ]
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 3,
                "type": "VEC3",
                "max": [1.0, 1.0, 0.0],
                "min": [0.0, 0.0, 0.0],
            },
            {
                "bufferView": 1,
                "componentType": 5123,
                "count": 3,
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 36, "target": 34962},
            {"buffer": 0, "byteOffset": 36, "byteLength": 6, "target": 34963},
        ],
        "buffers": [{"byteLength": len(bin_blob)}],
    }
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "

    chunks = b""
    chunks += struct.pack("<I", len(json_bytes))
    chunks += struct.pack("<I", 0x4E4F534A)  # JSON
    chunks += json_bytes
    chunks += struct.pack("<I", len(bin_blob))
    chunks += struct.pack("<I", 0x004E4942)  # BIN\0
    chunks += bin_blob

    total_len = 12 + len(chunks)
    header = struct.pack("<4sII", b"glTF", 2, total_len)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + chunks)
