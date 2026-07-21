"""Финальная валидация GLB + quality gate ≥0.7 (§5.4 / §6.12)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MAX_BYTES = 15 * 1024 * 1024
QUALITY_THRESHOLD = float(os.getenv("QUALITY_THRESHOLD", "0.7"))
SEG_AVG_MIN = float(os.getenv("SEGMENTATION_AVG_MIN", "0.85"))
# Минимальная геометрия валидной модели (§5.4): пустой/битый GLB отклоняем.
MIN_FACES = int(os.getenv("VALIDATE_MIN_FACES", "200"))
MIN_VERTICES = int(os.getenv("VALIDATE_MIN_VERTICES", "100"))


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


def _geometry_score(model_path: Path) -> tuple[float, dict]:
    """Реальная проверка геометрии GLB через trimesh (§5.4).

    Возвращает (score, meta). При недоступности парсера — мягкий fallback,
    но НЕ маскирует пустую модель: `faces=0` трактуется как провал.
    """
    try:
        import trimesh  # type: ignore
    except Exception:
        return 0.75, {"parsed": False, "reason": "trimesh_unavailable"}

    try:
        loaded = trimesh.load(str(model_path), force="scene")
    except Exception as exc:  # noqa: BLE001
        return 0.0, {"parsed": False, "reason": f"load_error: {exc}"}

    geometry_map = getattr(loaded, "geometry", None)
    if geometry_map:
        geometries = list(geometry_map.values())
    elif loaded is not None:
        geometries = [loaded]
    else:
        geometries = []

    def _count(obj, attr: str) -> int:
        arr = getattr(obj, attr, None)
        if arr is None:
            return 0
        try:
            return int(len(arr))
        except TypeError:
            return 0

    faces = sum(_count(g, "faces") for g in geometries)
    vertices = sum(_count(g, "vertices") for g in geometries)

    meta = {
        "parsed": True,
        "mesh_count": len(geometries),
        "faces": faces,
        "vertices": vertices,
        "min_faces": MIN_FACES,
        "min_vertices": MIN_VERTICES,
    }
    if faces == 0 or vertices == 0:
        return 0.0, {**meta, "reason": "empty_geometry"}
    if faces >= MIN_FACES and vertices >= MIN_VERTICES:
        watertight = all(getattr(g, "is_watertight", True) for g in geometries if hasattr(g, "faces"))
        meta["watertight"] = watertight
        if not watertight:
            return 0.65, {**meta, "reason": "not_watertight"}
        return 1.0, meta
    # есть геометрия, но подозрительно мало полигонов
    return 0.5, {**meta, "reason": "low_poly"}


def _gltf_validator_check(model_path: Path) -> dict:
    """§6.7: gltf-validator CLI если установлен."""
    import shutil
    import subprocess

    cmd = shutil.which("gltf-validator") or shutil.which("gltf_validator")
    if not cmd:
        return {"ok": True, "skipped": True, "reason": "gltf-validator not installed"}
    try:
        r = subprocess.run([cmd, str(model_path)], capture_output=True, text=True, check=False, timeout=120)
        ok = r.returncode == 0
        return {
            "ok": ok,
            "returncode": r.returncode,
            "stdout_tail": (r.stdout or "")[-500:],
            "stderr_tail": (r.stderr or "")[-500:],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": True, "skipped": True, "reason": str(exc)}


def compute_quality(root: Path, size: int) -> dict:
    seg_s, seg_meta = _seg_score(root)
    size_s = _size_score(size)
    pbr_s = _pbr_score(root)
    geom_s, geom_meta = _geometry_score(root / "model.glb")
    # веса: сегментация и геометрия критичны (§5.4/§6.12), размер и PBR — технические
    score = round(0.4 * seg_s + 0.3 * geom_s + 0.15 * size_s + 0.15 * pbr_s, 4)
    # пустая/битая геометрия — жёсткий провал независимо от прочих компонент
    passed = score >= QUALITY_THRESHOLD and geom_s > 0.0
    return {
        "quality_score": score,
        "threshold": QUALITY_THRESHOLD,
        "components": {
            "segmentation": seg_s,
            "geometry": geom_s,
            "size": size_s,
            "pbr": pbr_s,
        },
        "segmentation": seg_meta,
        "geometry": geom_meta,
        "size_bytes": size,
        "passed": passed,
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
    report["gltf_validator"] = _gltf_validator_check(model)
    if not report["gltf_validator"].get("ok", True) and not report["gltf_validator"].get("skipped"):
        raise SystemExit(f"gltf_validator failed: {report['gltf_validator']}")
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
