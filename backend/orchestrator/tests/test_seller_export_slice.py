"""Seller ZIP export §7.7."""

import json
import zipfile
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.seller_export import INSTRUCTION_TEXT, build_publish_zip


def test_build_publish_zip_contents():
    model = SimpleNamespace(
        uuid="m-1",
        order_id=42,
        company_id=7,
        publish_status="not_published",
        glb_url="s3://models/m-1/final/model.glb",
        usdz_url="s3://models/m-1/final/model.usdz",
    )
    with patch(
        "app.services.seller_export._load_model_files",
        return_value=(b"glb-data", b"usdz-data"),
    ):
        raw = build_publish_zip(model)
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        names = set(zf.namelist())
        assert names == {"model.glb", "model.usdz", "INSTRUCTION.txt", "metadata.json"}
        assert zf.read("model.glb") == b"glb-data"
        assert INSTRUCTION_TEXT.encode() in zf.read("INSTRUCTION.txt")
        meta = json.loads(zf.read("metadata.json"))
        assert meta["model_uuid"] == "m-1"
        assert meta["order_id"] == 42
        assert meta["company_id"] == 7


def test_build_publish_zip_requires_glb():
    model = SimpleNamespace(glb_url=None, usdz_url=None)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        build_publish_zip(model)
    assert exc.value.status_code == 400
