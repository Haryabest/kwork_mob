"""
Обёртка TRELLIS для воркера (§5.5).

Поддерживает:
  - microsoft/TRELLIS: trellis.pipelines.TrellisImageTo3DPipeline
  - пакетный API: from trellis import TrellisPipeline

Env:
  TRELLIS_ROOT=/app/trellis
  TRELLIS_WEIGHTS=JeffreyXiang/TRELLIS-image-large  (HF id или локальный путь)
  WORKER_PIPELINE_MODE=trellis
  TRELLIS_ALLOW_STUB_FALLBACK=0
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("trellis_runtime")

_pipeline = None
_pipeline_kind = None


def _ensure_path() -> Path:
    root = Path(os.getenv("TRELLIS_ROOT", "/app/trellis"))
    if root.exists() and str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def get_pipeline():
    global _pipeline, _pipeline_kind
    if _pipeline is not None:
        return _pipeline

    _ensure_path()
    import torch

    weights = os.getenv("TRELLIS_WEIGHTS", "JeffreyXiang/TRELLIS-image-large")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Loading TRELLIS device=%s weights=%s", device, weights)

    # 1) официальный microsoft TRELLIS image→3D
    try:
        from trellis.pipelines import TrellisImageTo3DPipeline  # type: ignore

        pipe = TrellisImageTo3DPipeline.from_pretrained(weights)
        if hasattr(pipe, "cuda") and device == "cuda":
            pipe.cuda()
        _pipeline = pipe
        _pipeline_kind = "image_to_3d"
        return _pipeline
    except Exception as exc:
        logger.info("TrellisImageTo3DPipeline unavailable: %s", exc)

    # 2) упрощённый TrellisPipeline
    try:
        from trellis import TrellisPipeline  # type: ignore

        try:
            _pipeline = TrellisPipeline.from_pretrained(weights, device=device)
        except Exception:
            try:
                _pipeline = TrellisPipeline(weights_dir=weights, device=device)
            except Exception:
                _pipeline = TrellisPipeline()
                if hasattr(_pipeline, "to"):
                    _pipeline.to(device)
        _pipeline_kind = "trellis_pipeline"
        return _pipeline
    except Exception as exc:
        raise ImportError(
            "TRELLIS не установлен. Соберите образ:\n"
            "  docker build --build-arg INSTALL_TRELLIS=1 --build-arg DOWNLOAD_WEIGHTS=1 -t kwork-worker .\n"
            "Или смонтируйте клон microsoft/TRELLIS в TRELLIS_ROOT.\n"
            f"Детали: {exc}"
        ) from exc


def _export_result(result, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(result, (str, Path)):
        src = Path(result)
        if src.resolve() != output.resolve():
            output.write_bytes(src.read_bytes())
        return
    if isinstance(result, dict):
        # microsoft TRELLIS: outputs['gaussian'] / mesh
        mesh = result.get("mesh") or result.get("glb") or result.get("model")
        if mesh is not None:
            return _export_result(mesh, output)
        gaussians = result.get("gaussian")
        if gaussians is not None and hasattr(gaussians, "save_ply"):
            # конвертация через trimesh если есть mesh-экспорт
            if hasattr(gaussians, "to_mesh"):
                return _export_result(gaussians.to_mesh(), output)
        raise RuntimeError(f"TRELLIS dict без mesh: keys={list(result.keys())}")
    if hasattr(result, "export"):
        result.export(str(output))
        return
    if hasattr(result, "save"):
        result.save(str(output))
        return
    # list of meshes
    if isinstance(result, (list, tuple)) and result:
        return _export_result(result[0], output)
    raise RuntimeError(f"Не удалось сохранить результат TRELLIS: {type(result)}")


def run_trellis(task_dir: Path, output: Path) -> Path:
    """Multi-view / single-view → raw_mesh.glb. photos_nobg предпочтительнее photos."""
    import torch
    from PIL import Image

    photos_dir = task_dir / "photos_nobg"
    if not photos_dir.exists() or not any(photos_dir.iterdir()):
        photos_dir = task_dir / "photos"

    images = sorted(
        [
            p
            for p in photos_dir.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
    )
    if not images:
        raise RuntimeError(f"Нет изображений в {photos_dir}")

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    pipe = get_pipeline()
    paths = [str(p) for p in images]
    pil_images = [Image.open(p).convert("RGBA") for p in images]

    result = None
    if _pipeline_kind == "image_to_3d":
        # multi-view: пробуем все кадры; иначе первый (фронт)
        if hasattr(pipe, "run_multi_image"):
            result = pipe.run_multi_image(pil_images)
        elif hasattr(pipe, "run"):
            try:
                result = pipe.run(pil_images)
            except Exception:
                result = pipe.run(pil_images[0])
        else:
            raise RuntimeError("TrellisImageTo3DPipeline: нет run/run_multi_image")
    elif hasattr(pipe, "run"):
        try:
            result = pipe.run(paths)
        except Exception:
            result = pipe.run(pil_images)
    elif hasattr(pipe, "generate"):
        result = pipe.generate(paths)
    elif callable(pipe):
        result = pipe(paths)
    else:
        raise RuntimeError("TrellisPipeline: неизвестный API")

    _export_result(result, output)

    if not output.exists() or output.stat().st_size < 100:
        # иногда pipeline пишет .ply — конвертим
        ply = output.with_suffix(".ply")
        if not ply.exists():
            raise RuntimeError("TRELLIS вернул пустой GLB")
        try:
            import trimesh

            mesh = trimesh.load(str(ply))
            mesh.export(str(output))
        except Exception as exc:
            raise RuntimeError(f"TRELLIS GLB пуст, PLY convert failed: {exc}") from exc

    return output
