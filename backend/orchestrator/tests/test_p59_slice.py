"""§6.7 gltf_validator, §7.4 publish guide CMS, §7.5 corp notes."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def test_publish_guide_default_marketplace():
    from app.services.publish_guide import DEFAULT_GUIDES, _norm_marketplace

    assert _norm_marketplace("wildberries") == "wb"
    assert "Wildberries" in DEFAULT_GUIDES["wb"]


@pytest.mark.asyncio
async def test_get_publish_guide_no_db_doc(db):
    from app.services.publish_guide import get_publish_guide

    out = await get_publish_guide(db, marketplace="ozon")
    assert out["marketplace"] == "ozon"
    assert out["body"]
    assert out["source"] == "default"


def test_gltf_validator_skips_when_missing(tmp_path):
    scripts = Path(__file__).resolve().parents[3] / "worker" / "scripts"
    spec = importlib.util.spec_from_file_location("validate_glb", scripts / "validate_glb.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    glb = tmp_path / "model.glb"
    glb.write_bytes(b"glTF" + b"\x00" * 8)
    out = mod._gltf_validator_check(glb)
    assert out.get("skipped") or out.get("ok")
