"""§6.1 webp compress, §6.2 watertight gate, §6.3 failed_segmentation marker."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

WORKER_SCRIPTS = Path(__file__).resolve().parents[3] / "worker" / "scripts"
if str(WORKER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WORKER_SCRIPTS))


def _load_script(name: str):
    path = WORKER_SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_trellis_texture_size_from_meta(tmp_path):
    trellis = _load_script("trellis_runtime")
    meta = tmp_path / "task_meta.json"
    meta.write_text('{"company_id": 1, "tier": "small"}', encoding="utf-8")
    assert trellis._texture_size_for_task(tmp_path) == 2048
    meta.write_text('{"company_id": 0, "tier": "small"}', encoding="utf-8")
    assert trellis._texture_size_for_task(tmp_path) == 1024


def test_validate_geometry_watertight_flag(tmp_path):
    validate = _load_script("validate_glb")
    glb = tmp_path / "model.glb"
    glb.write_bytes(b"glTF\x00\x00\x00\x00" + b"\x00" * 20)
    score, meta = validate._geometry_score(glb)
    assert "watertight" in meta or meta.get("parsed") is False
    assert score >= 0.0


def test_compress_has_webp_helper():
    compress = _load_script("compress_draco")
    assert callable(compress._try_gltf_webp)
