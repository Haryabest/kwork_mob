"""NSFW scan текстур импортированного GLB §6.10 / §10.8 (optional worker step)."""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

from PIL import Image


def _nsfw_mode() -> str:
    return os.getenv("NSFW_MODE", "auto").strip().lower()


def _nsfw_threshold() -> float:
    try:
        return float(os.getenv("NSFW_THRESHOLD", "0.55"))
    except ValueError:
        return 0.55


def _skin_ratio(data: bytes) -> float:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    cx0, cy0 = int(w * 0.2), int(h * 0.15)
    cx1, cy1 = int(w * 0.8), int(h * 0.85)
    crop = img.crop((cx0, cy0, cx1, cy1))
    pixels = list(crop.getdata())
    if not pixels:
        return 0.0
    skin = 0
    for r, g, b in pixels:
        if (
            r > 95
            and g > 40
            and b > 20
            and max(r, g, b) - min(r, g, b) > 15
            and abs(r - g) > 15
            and r > g
            and r > b
        ):
            skin += 1
    return skin / len(pixels)


def _score_nudenet(data: bytes) -> float | None:
    try:
        from nudenet import NudeDetector  # type: ignore
    except Exception:
        return None
    import tempfile

    try:
        detector = NudeDetector()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tex.jpg"
            Image.open(io.BytesIO(data)).convert("RGB").save(p, format="JPEG", quality=90)
            dets = detector.detect(str(p))
        bad = {
            "FEMALE_GENITALIA_EXPOSED",
            "MALE_GENITALIA_EXPOSED",
            "BUTTOCKS_EXPOSED",
            "FEMALE_BREAST_EXPOSED",
            "ANUS_EXPOSED",
        }
        scores = [float(d.get("score") or 0) for d in (dets or []) if d.get("class") in bad]
        return max(scores) if scores else 0.0
    except Exception:
        return None


def _analyze_image(name: str, data: bytes) -> dict:
    if b"NSFW_TEST_BLOCK" in data[:4096]:
        return {"name": name, "is_nsfw": True, "confidence": 1.0, "method": "marker"}

    mode = _nsfw_mode()
    if mode == "off":
        return {"name": name, "is_nsfw": False, "confidence": 0.0, "method": "off"}

    threshold = _nsfw_threshold()
    confidence = 0.0
    method = "none"

    if mode in ("nudenet", "auto"):
        nn = _score_nudenet(data)
        if nn is not None:
            confidence = nn
            method = "nudenet"

    if method == "none" or (mode in ("heuristic", "auto") and confidence < threshold):
        skin = _skin_ratio(data)
        if skin > confidence:
            confidence = skin
            method = "skin_heuristic"

    return {
        "name": name,
        "is_nsfw": confidence >= threshold,
        "confidence": round(confidence, 4),
        "method": method,
    }


def _extract_texture_bytes(glb: Path) -> list[tuple[str, bytes]]:
    try:
        from pygltflib import GLTF2
    except ImportError:
        return []
    try:
        gltf = GLTF2().load(str(glb))
    except Exception:
        return []
    out: list[tuple[str, bytes]] = []
    blob = gltf.binary_blob() or b""
    for idx, img_def in enumerate(gltf.images or []):
        data = None
        if img_def.uri and img_def.uri.startswith("data:"):
            import base64

            data = base64.b64decode(img_def.uri.split(",", 1)[-1])
        elif img_def.bufferView is not None and gltf.bufferViews:
            bv = gltf.bufferViews[img_def.bufferView]
            if blob:
                data = blob[bv.byteOffset : bv.byteOffset + bv.byteLength]
        if data and len(data) > 100:
            out.append((f"texture_{idx}", data))
    return out[:8]


def main(task_dir: str) -> None:
    root = Path(task_dir)
    meta_path = root / "task_meta.json"
    category = "other"
    if meta_path.exists():
        try:
            category = (json.loads(meta_path.read_text(encoding="utf-8")).get("category") or "other").lower()
        except Exception:
            category = "other"

    glb = root / "model.glb"
    if not glb.exists():
        raise SystemExit("model.glb missing for NSFW scan")

    if category == "adult":
        report = {"skipped": True, "reason": "adult_category", "category": category, "is_nsfw": False}
        (root / "import_nsfw_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("[scan_import_nsfw] skip adult category")
        return

    textures = _extract_texture_bytes(glb)
    frames = [_analyze_image(name, data) for name, data in textures]
    worst = max(frames, key=lambda f: f.get("confidence") or 0) if frames else None
    is_nsfw = any(f.get("is_nsfw") for f in frames)

    report = {
        "category": category,
        "textures_scanned": len(frames),
        "is_nsfw": is_nsfw,
        "confidence": worst.get("confidence") if worst else 0.0,
        "method": worst.get("method") if worst else "none",
        "trigger": worst.get("name") if worst else None,
        "frames": frames,
    }
    (root / "import_nsfw_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[scan_import_nsfw] scanned={len(frames)} nsfw={is_nsfw}")
    if is_nsfw:
        conf = report.get("confidence", 0)
        raise SystemExit(f"import_nsfw_detected confidence={conf} method={report.get('method')}")


if __name__ == "__main__":
    main(sys.argv[1])
