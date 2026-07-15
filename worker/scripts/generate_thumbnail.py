"""thumbnail.jpg 512×512 при генерации §9.2.1 / §19.4.3."""

from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image

SIZE = 512


def _fit_square(img: Image.Image, size: int) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    if w <= 0 or h <= 0:
        return Image.new("RGB", (size, size), (210, 210, 210))
    scale = max(size / w, size / h)
    nw, nh = int(w * scale), int(h * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - size) // 2
    top = (nh - size) // 2
    return img.crop((left, top, left + size, top + size))


def _photo_source(root: Path) -> Path | None:
    for rel in (
        "photos_nobg/view_00.png",
        "photos_nobg/view_00.jpg",
        "photos/view_00.jpg",
        "photos/view_00.png",
        "photos/view_00.webp",
    ):
        p = root / rel
        if p.exists() and p.stat().st_size > 100:
            return p
    return None


def _glb_texture_image(glb: Path) -> Image.Image | None:
    if not glb.exists():
        return None
    try:
        from pygltflib import GLTF2
    except ImportError:
        return None
    try:
        gltf = GLTF2().load(str(glb))
    except Exception:
        return None
    if not gltf.images:
        return None
    img_def = gltf.images[0]
    data = None
    if img_def.uri and img_def.uri.startswith("data:"):
        import base64

        b64 = img_def.uri.split(",", 1)[-1]
        data = base64.b64decode(b64)
    elif img_def.bufferView is not None and gltf.bufferViews and gltf.buffers:
        bv = gltf.bufferViews[img_def.bufferView]
        blob = gltf.binary_blob() or b""
        if blob:
            data = blob[bv.byteOffset : bv.byteOffset + bv.byteLength]
    if not data:
        return None
    try:
        return Image.open(io.BytesIO(data))
    except Exception:
        return None


def main(task_dir: str) -> None:
    root = Path(task_dir)
    out_dir = root / "final"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "thumbnail.jpg"

    src = _photo_source(root)
    if src:
        img = Image.open(src)
    else:
        img = _glb_texture_image(root / "model.glb")
        if img is None:
            img = Image.new("RGB", (SIZE, SIZE), (200, 200, 205))

    thumb = _fit_square(img, SIZE)
    thumb.save(out, "JPEG", quality=88, optimize=True)
    print(f"[generate_thumbnail] {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main(sys.argv[1])
