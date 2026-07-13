"""Проверка DWT-знака в diffuse (§5.12 / §10.5).

CLI: python verify_watermark.py <image.png|glb> [--bits 128] [--expected-meta user:company:order:ts]
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

# allow import from same dir
sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_watermark import _bits_from_meta, extract_bits_dwt  # noqa: E402


def _bit_match_ratio(a: list[int], b: list[int]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    return sum(1 for i in range(n) if a[i] == b[i]) / n


def load_diffuse_from_glb(path: Path) -> Image.Image | None:
    try:
        from pygltflib import GLTF2
    except Exception:
        return None
    gltf = GLTF2().load(str(path))
    image_index = None
    if gltf.materials:
        for mat in gltf.materials:
            pbr = getattr(mat, "pbrMetallicRoughness", None)
            if not pbr:
                continue
            bct = getattr(pbr, "baseColorTexture", None)
            if bct is not None and getattr(bct, "index", None) is not None:
                image_index = gltf.textures[bct.index].source
                break
    if image_index is None or not gltf.images:
        return None
    img = gltf.images[image_index]
    raw = None
    uri = getattr(img, "uri", None)
    if uri and isinstance(uri, str) and uri.startswith("data:"):
        raw = base64.b64decode(uri.split(",", 1)[1])
    elif getattr(img, "bufferView", None) is not None:
        bv = gltf.bufferViews[img.bufferView]
        blob = gltf.binary_blob()
        if blob is not None:
            off = int(getattr(bv, "byteOffset", 0) or 0)
            raw = bytes(blob[off : off + int(bv.byteLength)])
    if not raw:
        return None
    return Image.open(io.BytesIO(raw)).convert("RGB")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--bits", type=int, default=128)
    p.add_argument("--user-id", type=int, default=None)
    p.add_argument("--company-id", type=int, default=0)
    p.add_argument("--order-id", type=int, default=None)
    p.add_argument("--timestamp", type=int, default=None)
    p.add_argument("--min-ratio", type=float, default=0.80)
    args = p.parse_args()

    path = Path(args.path)
    if path.suffix.lower() in {".glb", ".gltf"}:
        img = load_diffuse_from_glb(path)
        if img is None:
            raise SystemExit("no diffuse in glb")
        # HMAC extras
        try:
            from pygltflib import GLTF2

            gltf = GLTF2().load(str(path))
            extras = gltf.extras if isinstance(gltf.extras, dict) else {}
            print(json.dumps({"extras": extras}, ensure_ascii=False))
            if args.user_id is None and extras.get("user_id") is not None:
                args.user_id = int(extras["user_id"])
            if args.order_id is None and extras.get("order_id") is not None:
                args.order_id = int(extras["order_id"])
            if args.timestamp is None and extras.get("timestamp") is not None:
                args.timestamp = int(extras["timestamp"])
            if extras.get("company_id") is not None:
                args.company_id = int(extras["company_id"] or 0)
        except Exception:  # noqa: BLE001
            pass
    else:
        img = Image.open(path).convert("RGB")

    extracted = extract_bits_dwt(img, n_bits=args.bits)
    result = {"bits_extracted": len(extracted), "ok": None, "ratio": None}

    if args.user_id is not None and args.order_id is not None and args.timestamp is not None:
        expected = _bits_from_meta(args.user_id, args.company_id or 0, args.order_id, args.timestamp, args.bits)
        ratio = _bit_match_ratio(extracted, expected)
        result["ratio"] = ratio
        result["ok"] = ratio >= args.min_ratio
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(0 if result["ok"] else 2)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
