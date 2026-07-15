#!/usr/bin/env python3
"""Minimal PNG placeholders without Pillow (stdlib only)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCREENS = ("home_shoot", "guided_dome", "queue", "model_viewer", "publish")
COLORS = {
    "home_shoot": (18, 24, 38),
    "guided_dome": (24, 32, 48),
    "queue": (20, 36, 52),
    "model_viewer": (16, 28, 44),
    "publish": (22, 30, 46),
}


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def write_solid_png(path: Path, width: int, height: int, rgb: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    r, g, b = rgb
    row = b"\x00" + bytes([r, g, b]) * width
    raw = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", zlib.compress(raw, 9))
    png += _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    for name in SCREENS:
        color = COLORS[name]
        write_solid_png(ROOT / "android" / f"{name}.png", 1080, 1920, color)
        write_solid_png(ROOT / "ios" / f"{name}.png", 1290, 2796, color)
    print(f"Wrote {len(SCREENS) * 2} PNG placeholders under {ROOT}")


if __name__ == "__main__":
    main()
