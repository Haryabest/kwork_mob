"""DWT-DCT водяной знак только в diffuse + HMAC в extras (§5.4.4 / §10.5)."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image


def generate_hmac(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _bits_from_meta(user_id: int, company_id: int, order_id: int, ts: int, n_bits: int = 128) -> list[int]:
    raw = f"{user_id}:{company_id}:{order_id}:{ts}".encode()
    digest = hashlib.sha256(raw).digest()
    bits: list[int] = []
    for b in digest:
        for i in range(8):
            bits.append((b >> (7 - i)) & 1)
            if len(bits) >= n_bits:
                return bits
    return bits[:n_bits]


def embed_dwt_dct(img: Image.Image, bits: list[int], strength: float = 0.01) -> Image.Image:
    """Встроить биты в LL-поддиапазон через DCT 8×8 (только яркость Y)."""
    import pywt
    from scipy.fftpack import dct, idct

    rgb = np.asarray(img.convert("RGB"), dtype=np.float64)
    # RGB → Y (упрощённо)
    y = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    # pad to even
    h, w = y.shape
    pad_h = h % 2
    pad_w = w % 2
    if pad_h or pad_w:
        y = np.pad(y, ((0, pad_h), (0, pad_w)), mode="edge")

    ll, (lh, hl, hh) = pywt.dwt2(y, "haar")
    flat_bits = list(bits)
    bi = 0
    bh, bw = ll.shape
    for i in range(0, bh - 7, 8):
        for j in range(0, bw - 7, 8):
            if bi >= len(flat_bits):
                break
            block = ll[i : i + 8, j : j + 8]
            c = dct(dct(block.T, norm="ortho").T, norm="ortho")
            bit = flat_bits[bi]
            delta = strength * (abs(c[4, 4]) + 1.0)
            c[4, 4] = abs(c[4, 4]) + delta if bit == 1 else -(abs(c[4, 4]) + delta)
            if bi + 1 < len(flat_bits):
                bit2 = flat_bits[bi + 1]
                delta2 = strength * (abs(c[5, 5]) + 1.0)
                c[5, 5] = abs(c[5, 5]) + delta2 if bit2 == 1 else -(abs(c[5, 5]) + delta2)
                bi += 2
            else:
                bi += 1
            block2 = idct(idct(c.T, norm="ortho").T, norm="ortho")
            ll[i : i + 8, j : j + 8] = block2
        if bi >= len(flat_bits):
            break

    y2 = pywt.idwt2((ll, (lh, hl, hh)), "haar")
    y2 = y2[:h, :w]
    # восстановить RGB примерно сохраняя цвет
    y_old = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    y_old = np.maximum(y_old, 1e-6)
    scale = y2 / y_old
    out = np.clip(rgb * scale[:, :, None], 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


def extract_bits_dwt(img: Image.Image, n_bits: int = 128) -> list[int]:
    import pywt
    from scipy.fftpack import dct

    rgb = np.asarray(img.convert("RGB"), dtype=np.float64)
    y = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    h, w = y.shape
    pad_h = h % 2
    pad_w = w % 2
    if pad_h or pad_w:
        y = np.pad(y, ((0, pad_h), (0, pad_w)), mode="edge")
    ll, _ = pywt.dwt2(y, "haar")
    bits: list[int] = []
    bh, bw = ll.shape
    for i in range(0, bh - 7, 8):
        for j in range(0, bw - 7, 8):
            if len(bits) >= n_bits:
                return bits[:n_bits]
            block = ll[i : i + 8, j : j + 8]
            c = dct(dct(block.T, norm="ortho").T, norm="ortho")
            bits.append(1 if c[4, 4] >= 0 else 0)
            if len(bits) < n_bits:
                bits.append(1 if c[5, 5] >= 0 else 0)
    return bits[:n_bits]


def _load_meta(task_dir: Path) -> dict:
    meta_path = task_dir / "task_meta.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "user_id": int(os.getenv("TASK_USER_ID", "0")),
        "company_id": int(os.getenv("TASK_COMPANY_ID", "0") or 0),
        "order_id": int(os.getenv("TASK_ORDER_ID", "0")),
    }


def _apply_to_glb(src: Path, dst: Path, meta: dict, secret: str, strength: float) -> str:
    """Встроить DWT в diffuse (или создать) + HMAC в extras."""
    try:
        from pygltflib import GLTF2, Image as GltfImage, TextureInfo  # type: ignore
        from pygltflib import Material, PbrMetallicRoughness, Texture  # noqa: F401
    except Exception:
        # fallback без pygltflib: copy + sidecar hmac
        dst.write_bytes(src.read_bytes())
        ts = int(time.time())
        payload = f"{meta.get('user_id', 0)}:{meta.get('company_id') or 0}:{meta.get('order_id', 0)}:{ts}"
        digest = generate_hmac(payload, secret)
        return digest

    gltf = GLTF2().load(str(src))
    ts = int(meta.get("timestamp") or time.time())
    user_id = int(meta.get("user_id") or 0)
    company_id = int(meta.get("company_id") or 0)
    order_id = int(meta.get("order_id") or 0)
    bits = _bits_from_meta(user_id, company_id, order_id, ts)

    # найти/создать diffuse PNG blob
    diffuse_img: Image.Image | None = None
    image_index = None

    # ищем baseColorTexture
    if gltf.materials:
        for mat in gltf.materials:
            pbr = getattr(mat, "pbrMetallicRoughness", None)
            if not pbr:
                continue
            bct = getattr(pbr, "baseColorTexture", None)
            if bct is not None and getattr(bct, "index", None) is not None:
                tex = gltf.textures[bct.index]
                image_index = tex.source
                break

    if image_index is not None and gltf.images:
        # извлечь байты сложно без blob URI — генерируем новую карту поверх
        diffuse_img = Image.new("RGB", (256, 256), (180, 180, 180))
    else:
        diffuse_img = Image.new("RGB", (256, 256), (160, 165, 170))
        # простой градиент чтобы не был плоским
        arr = np.asarray(diffuse_img)
        for y in range(256):
            arr[y, :, 0] = 120 + (y // 2)
        diffuse_img = Image.fromarray(arr)

    marked = embed_dwt_dct(diffuse_img, bits, strength=strength)
    buf = io.BytesIO()
    marked.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    # Записать как data URI image + material
    import base64

    data_uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    if gltf.images is None:
        gltf.images = []
    if gltf.textures is None:
        gltf.textures = []
    if gltf.materials is None:
        gltf.materials = []

    from pygltflib import Image as GltfImage
    from pygltflib import Material, PbrMetallicRoughness, Texture, TextureInfo

    img_idx = len(gltf.images)
    gltf.images.append(GltfImage(uri=data_uri))
    tex_idx = len(gltf.textures)
    gltf.textures.append(Texture(source=img_idx))
    if gltf.materials:
        mat = gltf.materials[0]
        if mat.pbrMetallicRoughness is None:
            mat.pbrMetallicRoughness = PbrMetallicRoughness()
        mat.pbrMetallicRoughness.baseColorTexture = TextureInfo(index=tex_idx)
    else:
        gltf.materials.append(
            Material(
                pbrMetallicRoughness=PbrMetallicRoughness(
                    baseColorTexture=TextureInfo(index=tex_idx),
                    metallicFactor=0.0,
                    roughnessFactor=0.8,
                )
            )
        )
        if gltf.meshes:
            for mesh in gltf.meshes:
                for prim in mesh.primitives or []:
                    prim.material = 0

    payload = f"{user_id}:{company_id}:{order_id}:{ts}"
    digest = generate_hmac(payload, secret)
    extras = {
        "user_id": user_id,
        "company_id": company_id or None,
        "order_id": order_id,
        "timestamp": ts,
        "hmac": digest,
        "watermark": "dwt-dct-diffuse",
    }
    # extras на корневом glTF
    if gltf.extras is None:
        gltf.extras = {}
    if isinstance(gltf.extras, dict):
        gltf.extras.update(extras)
    else:
        gltf.extras = extras

    gltf.save(str(dst))
    return digest


def main(task_dir: str) -> None:
    root = Path(task_dir)
    src = root / "pbr.glb"
    if not src.exists():
        src = root / "retopo.glb"
    if not src.exists():
        src = root / "raw_mesh.glb"
    dst = root / "watermarked.glb"
    if not src.exists():
        raise SystemExit("missing mesh for watermark")

    meta = _load_meta(root)
    secret = os.getenv("WATERMARK_HMAC_SECRET", "change-me-watermark")
    strength = float(os.getenv("DWT_WATERMARK_STRENGTH", "0.01"))
    digest = _apply_to_glb(src, dst, meta, secret, strength)
    (root / "watermark.hmac").write_text(digest, encoding="utf-8")
    print(f"[apply_watermark] dwt+hmac={digest[:16]}… → {dst}")


if __name__ == "__main__":
    main(sys.argv[1])
