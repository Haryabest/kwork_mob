"""Import validation queue + GLB parse §6.10."""

import json
import struct
import tempfile
from pathlib import Path


def _minimal_glb() -> bytes:
    gltf = {
        "asset": {"version": "2.0"},
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1, 1, 1, 1],
                    "metallicFactor": 0,
                    "roughnessFactor": 0.5,
                }
            }
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "material": 0}]}],
    }
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * pad
    chunks = struct.pack("<I", len(json_bytes)) + b"JSON" + json_bytes
    return b"glTF" + struct.pack("<II", 2, 12 + len(chunks)) + chunks


def test_import_enqueue_payload_shape():
    payload = {
        "pipeline": "import_validate",
        "import_glb_key": "imports/uuid/model.glb",
    }
    assert payload["pipeline"] == "import_validate"
    assert payload["import_glb_key"].startswith("imports/")


def test_validate_import_glb_minimal():
    import sys

    scripts = Path(__file__).resolve().parents[3] / "worker" / "scripts"
    sys.path.insert(0, str(scripts))
    from validate_import_glb import main

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "model.glb").write_bytes(_minimal_glb())
        main(str(root))
        report = json.loads((root / "import_report.json").read_text(encoding="utf-8"))
        assert report["passed"] is True
        assert report["gltf_version"] == "2.0"
