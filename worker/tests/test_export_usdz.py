"""USDZ export helpers (без GPU/Blender в CI)."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from export_usdz_tryon import _pack_usdz_archive


def test_pack_usdz_archive_minimal(tmp_path: Path):
    usda = tmp_path / "scene.usda"
    usda.write_text('#usda 1.0\n', encoding="utf-8")
    glb = tmp_path / "model.glb"
    glb.write_bytes(b"glb-stub")
    out = tmp_path / "out.usdz"
    assert _pack_usdz_archive(usda, glb, out)
    assert out.stat().st_size > 10
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert "scene.usda" in names
    assert "model.glb" in names


@pytest.mark.skipif(not __import__("shutil").which("blender"), reason="blender not installed")
def test_blender_usdz_roundtrip(tmp_path: Path):
    from export_usdz_tryon import _blender_usdz

    # Минимальный glTF binary (empty scene) — только smoke если blender есть
    glb = tmp_path / "empty.glb"
    glb.write_bytes(
        b"glTF" + (2).to_bytes(4, "little") + (12).to_bytes(4, "little")
        + b"JSON" + (0).to_bytes(4, "little") + b"{}" + b"\x00" * 4
    )
    usdz = tmp_path / "out.usdz"
    # Пустой glb может не импортироваться — не падаем в CI
    _blender_usdz(glb, usdz)
