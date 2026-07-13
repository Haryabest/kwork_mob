"""
Обёртка TRELLIS / TRELLIS.2 для воркера (§5.5 / §6.2).

Env:
  TRELLIS_VERSION=2                    # 2 = microsoft/TRELLIS.2-4B (клиент)
  TRELLIS_ROOT=/app/trellis
  TRELLIS_WEIGHTS=microsoft/TRELLIS.2-4B
  TRELLIS2_PIPELINE_TYPE=512           # 512|1024|1024_cascade|1536_cascade
  TRELLIS2_LOW_VRAM=1
  TRELLIS2_DECIMATION=300000
  TRELLIS2_TEXTURE_SIZE=2048
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
_pipeline_kind: str | None = None


def trellis_version() -> str:
    return os.getenv("TRELLIS_VERSION", "2").strip().lower()


def _ensure_path() -> Path:
    root = Path(os.getenv("TRELLIS_ROOT", "/app/trellis"))
    if root.exists() and str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def _pick_front_image(photos_dir: Path) -> Path:
    images = sorted(
        p
        for p in photos_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if not images:
        raise RuntimeError(f"Нет изображений в {photos_dir}")
    for p in images:
        if p.name.startswith("view_00"):
            return p
    return images[0]


def get_pipeline():
    global _pipeline, _pipeline_kind
    if _pipeline is not None:
        return _pipeline

    _ensure_path()
    import torch

    weights = os.getenv("TRELLIS_WEIGHTS", "microsoft/TRELLIS.2-4B")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ver = trellis_version()
    logger.info("Loading TRELLIS.%s device=%s weights=%s", ver, device, weights)

    if ver in ("2", "trellis2", "trellis.2"):
        try:
            from trellis2.pipelines import Trellis2ImageTo3DPipeline  # type: ignore

            low_vram = os.getenv("TRELLIS2_LOW_VRAM", "1").lower() in ("1", "true", "yes")
            pipe = Trellis2ImageTo3DPipeline.from_pretrained(weights)
            pipe.low_vram = low_vram
            if device == "cuda" and hasattr(pipe, "cuda"):
                pipe.cuda()
            elif hasattr(pipe, "to"):
                pipe.to(device)
            _pipeline = pipe
            _pipeline_kind = "trellis2_image_to_3d"
            return _pipeline
        except Exception as exc:
            raise ImportError(
                "TRELLIS.2 не установлен. Соберите GPU-образ:\n"
                "  docker build --build-arg INSTALL_TRELLIS=1 --build-arg TRELLIS_VERSION=2 "
                "-t kwork-worker:trellis2 .\n"
                "Repo: https://github.com/microsoft/TRELLIS.2\n"
                "Weights: microsoft/TRELLIS.2-4B\n"
                f"Детали: {exc}"
            ) from exc

    # TRELLIS v1 (legacy)
    weights_v1 = os.getenv("TRELLIS_WEIGHTS", "JeffreyXiang/TRELLIS-image-large")
    try:
        from trellis.pipelines import TrellisImageTo3DPipeline  # type: ignore

        pipe = TrellisImageTo3DPipeline.from_pretrained(weights_v1)
        if hasattr(pipe, "cuda") and device == "cuda":
            pipe.cuda()
        _pipeline = pipe
        _pipeline_kind = "image_to_3d"
        return _pipeline
    except Exception as exc:
        logger.info("TrellisImageTo3DPipeline unavailable: %s", exc)

    try:
        from trellis import TrellisPipeline  # type: ignore

        try:
            _pipeline = TrellisPipeline.from_pretrained(weights_v1, device=device)
        except Exception:
            _pipeline = TrellisPipeline()
            if hasattr(_pipeline, "to"):
                _pipeline.to(device)
        _pipeline_kind = "trellis_pipeline"
        return _pipeline
    except Exception as exc:
        raise ImportError(f"TRELLIS v1 недоступен: {exc}") from exc


def _export_trellis2_mesh(mesh, output: Path) -> None:
    import o_voxel  # type: ignore

    if hasattr(mesh, "simplify"):
        try:
            mesh.simplify(16_777_216)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TRELLIS.2 mesh.simplify skipped: %s", exc)

    decimation = int(os.getenv("TRELLIS2_DECIMATION", "300000"))
    texture_size = int(os.getenv("TRELLIS2_TEXTURE_SIZE", "2048"))

    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices,
        faces=mesh.faces,
        attr_volume=mesh.attrs,
        coords=mesh.coords,
        attr_layout=mesh.layout,
        voxel_size=mesh.voxel_size,
        aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=decimation,
        texture_size=texture_size,
        remesh=True,
        remesh_band=1,
        remesh_project=0,
        verbose=False,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    glb.export(str(output), extension_webp=True)


def _export_result(result, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(result, (str, Path)):
        src = Path(result)
        if src.resolve() != output.resolve():
            output.write_bytes(src.read_bytes())
        return
    if isinstance(result, dict):
        mesh = result.get("mesh") or result.get("glb") or result.get("model")
        if mesh is not None:
            return _export_result(mesh, output)
        raise RuntimeError(f"TRELLIS dict без mesh: keys={list(result.keys())}")
    if _pipeline_kind == "trellis2_image_to_3d":
        return _export_trellis2_mesh(result, output)
    if hasattr(result, "export"):
        result.export(str(output))
        return
    if hasattr(result, "save"):
        result.save(str(output))
        return
    if isinstance(result, (list, tuple)) and result:
        return _export_result(result[0], output)
    raise RuntimeError(f"Не удалось сохранить результат TRELLIS: {type(result)}")


def run_trellis2(task_dir: Path, output: Path) -> Path:
    """TRELLIS.2: image→3D с native PBR (один лучший ракурс из 12)."""
    import torch
    from PIL import Image

    photos_dir = task_dir / "photos_nobg"
    if not photos_dir.exists() or not any(photos_dir.iterdir()):
        photos_dir = task_dir / "photos"

    front = _pick_front_image(photos_dir)
    image = Image.open(front).convert("RGBA")
    logger.info(
        "TRELLIS.2 input=%s (из 12 ракурсов — фронт; multi-view в .2 пока single-image)",
        front.name,
    )

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    pipe = get_pipeline()
    pipeline_type = os.getenv("TRELLIS2_PIPELINE_TYPE", "512")
    meshes = pipe.run(image, preprocess_image=False, pipeline_type=pipeline_type)
    if not meshes:
        raise RuntimeError("TRELLIS.2 вернул пустой результат")

    _export_trellis2_mesh(meshes[0], output)
    if not output.exists() or output.stat().st_size < 1000:
        raise RuntimeError(f"TRELLIS.2 GLB слишком мал: {output}")
    logger.info("TRELLIS.2 → %s (%s bytes)", output, output.stat().st_size)
    return output


def run_trellis_v1(task_dir: Path, output: Path) -> Path:
    """TRELLIS v1: multi-view при наличии API."""
    import torch
    from PIL import Image

    photos_dir = task_dir / "photos_nobg"
    if not photos_dir.exists() or not any(photos_dir.iterdir()):
        photos_dir = task_dir / "photos"

    images = sorted(
        p
        for p in photos_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if not images:
        raise RuntimeError(f"Нет изображений в {photos_dir}")

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    pipe = get_pipeline()
    pil_images = [Image.open(p).convert("RGBA") for p in images]
    result = None

    if _pipeline_kind == "image_to_3d":
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
        result = pipe.run(pil_images)
    else:
        raise RuntimeError("TRELLIS v1: неизвестный API")

    _export_result(result, output)
    if not output.exists() or output.stat().st_size < 100:
        raise RuntimeError("TRELLIS v1 вернул пустой GLB")
    return output


def run_trellis(task_dir: Path, output: Path) -> Path:
    if trellis_version() in ("2", "trellis2", "trellis.2"):
        return run_trellis2(task_dir, output)
    return run_trellis_v1(task_dir, output)
