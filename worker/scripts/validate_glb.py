"""Финальная валидация GLB + quality gate ≥0.7 (§5.4 / §6.12)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MAX_BYTES = 15 * 1024 * 1024
QUALITY_THRESHOLD = float(os.getenv("QUALITY_THRESHOLD", "0.7"))
SEG_AVG_MIN = float(os.getenv("SEGMENTATION_AVG_MIN", "0.85"))


def _seg_score(root: Path) -> tuple[float, dict]:
    meta_path = root / "task_meta.json"
    if not meta_path.exists():
        return 0.5, {"present": False, "avg_confidence": None}
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    seg = meta.get("segmentation") or {}
    avg = float(seg.get("avg_confidence") or 0.0)
    # нормируем к [0,1]: 0.85 → 1.0 на шкале gate
    score = min(1.0, avg / SEG_AVG_MIN) if SEG_AVG_MIN > 0 else avg
    return score, {
        "present": True,
        "avg_confidence": avg,
        "threshold": SEG_AVG_MIN,
        "weak_frames": seg.get("weak_frames"),
    }


def _size_score(size: int) -> float:
    if size <= 12 or size > MAX_BYTES:
        return 0.0
    # предпочтительно 1–12 MB
    mb = size / (1024 * 1024)
    if mb < 0.05:
        return 0.3
    if mb <= 12:
        return 1.0
    return 0.5


def _pbr_score(root: Path) -> float:
    """Наличие PBR-артефактов после bake (если есть markers)."""
    markers = [
        root / "pbr_ok.flag",
        root / "textures" / "diffuse.webp",
        root / "textures" / "diffuse.png",
        root / "bake_meta.json",
    ]
    if any(p.exists() for p in markers):
        return 1.0
    # GLB с валидным magic уже есть — мягкий балл без явных карт
    return 0.75


def compute_quality(root: Path, size: int) -> dict:
    seg_s, seg_meta = _seg_score(root)
    size_s = _size_score(size)
    pbr_s = _pbr_score(root)
    # веса: сегментация критична (§6.12), размер и PBR — технические
    score = round(0.5 * seg_s + 0.25 * size_s + 0.25 * pbr_s, 4)
    return {
        "quality_score": score,
        "threshold": QUALITY_THRESHOLD,
        "components": {
            "segmentation": seg_s,
            "size": size_s,
            "pbr": pbr_s,
        },
        "segmentation": seg_meta,
        "size_bytes": size,
        "passed": score >= QUALITY_THRESHOLD,
    }


def main(task_dir: str) -> None:
    root = Path(task_dir)
    model = root / "model.glb"
    if not model.exists():
        raise SystemExit("model.glb missing")
    size = model.stat().st_size
    if size <= 12:
        raise SystemExit(f"model.glb too small: {size}")
    if size > MAX_BYTES:
        raise SystemExit(f"model.glb too large: {size} > {MAX_BYTES}")
    magic = model.read_bytes()[:4]
    if magic != b"glTF":
        raise SystemExit(f"invalid GLB magic: {magic!r}")
    hmac_file = root / "watermark.hmac"
    if not hmac_file.exists():
        raise SystemExit("watermark.hmac missing")

    report = compute_quality(root, size)
    report_path = root / "quality_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[validate_glb] ok size={size} quality_score={report['quality_score']} "
        f"threshold={QUALITY_THRESHOLD}"
    )
    if not report["passed"]:
        raise SystemExit(
            f"quality_gate_failed score={report['quality_score']} < {QUALITY_THRESHOLD}"
        )


if __name__ == "__main__":
    main(sys.argv[1])
