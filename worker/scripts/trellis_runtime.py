"""
Обёртка TRELLIS / TRELLIS.2 для воркера (§5.5 / §6.2).

Env:
  TRELLIS_VERSION=2                    # 2 = microsoft/TRELLIS.2-4B (клиент)
  TRELLIS_ROOT=/app/trellis
  TRELLIS_WEIGHTS=microsoft/TRELLIS.2-4B
  TRELLIS2_PIPELINE_TYPE=512           # 512|1024|1024_cascade|1536_cascade
  TRELLIS2_MAX_NUM_TOKENS=49152        # для 1536 на 16GB можно 32768
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


def _progress(msg: str) -> None:
    """Видно в docker logs (subprocess stdout + worker_agent)."""
    logger.info(msg)
    print(f"[trellis_runtime] {msg}", flush=True)


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


def preflight_cuda() -> None:
    """RTX Blackwell sm_120 требует PyTorch cu128 (§5.1 / production GPU)."""
    import torch

    if not torch.cuda.is_available():
        return
    major, minor = torch.cuda.get_device_capability(0)
    cuda_ver = getattr(torch.version, "cuda", None) or ""
    device = torch.cuda.get_device_name(0)
    logger.info("CUDA preflight: %s sm_%s%s torch.cuda=%s", device, major, minor, cuda_ver)
    if major >= 12 and "12.8" not in cuda_ver:
        raise RuntimeError(
            f"GPU {device} (sm_{major}{minor}) требует PyTorch cu128, "
            f"сейчас torch.cuda={cuda_ver!r}. "
            "Пересоберите образ: pip install torch --index-url "
            "https://download.pytorch.org/whl/cu128"
        )


def _require_nobg_dir(task_dir: Path) -> Path:
    """TRELLIS.2: один вход view_00 из photos_nobg после remove_background (§6.2)."""
    photos_nobg = task_dir / "photos_nobg"
    if not photos_nobg.is_dir() or not any(photos_nobg.iterdir()):
        raise RuntimeError(
            "TRELLIS.2 требует photos_nobg/view_00 — сначала выполните remove_background.py"
        )
    return photos_nobg


def _resolve_low_vram() -> bool:
    raw = os.getenv("TRELLIS2_LOW_VRAM")
    if raw is not None:
        return raw.lower() in ("1", "true", "yes")
    try:
        import torch

        if torch.cuda.is_available():
            gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            # RTX 5060 Ti / 5070 16GB — без low_vram часто OOM при inference
            return gb < 20.0
    except Exception:  # noqa: BLE001
        pass
    return True


def _skip_internal_rembg() -> bool:
    return os.getenv("TRELLIS_SKIP_INTERNAL_REMBG", "1").lower() in ("1", "true", "yes")


def _free_cuda_memory() -> None:
    import gc

    import torch

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        if hasattr(torch.cuda, "ipc_collect"):
            torch.cuda.ipc_collect()
        torch.cuda.synchronize()


def _drop_internal_rembg(pipe) -> None:
    """Внешний remove_background.py уже дал photos_nobg — не держим BiRefNet в VRAM."""
    if not _skip_internal_rembg():
        return
    rembg = getattr(pipe, "rembg_model", None)
    if rembg is None:
        return
    try:
        if hasattr(rembg, "cpu"):
            rembg.cpu()
        if hasattr(pipe, "models") and isinstance(pipe.models, dict):
            pipe.models.pop("rembg", None)
        pipe.rembg_model = None
        _free_cuda_memory()
        _progress("internal rembg_model dropped (external nobg pipeline)")
    except Exception as exc:  # noqa: BLE001
        logger.warning("drop internal rembg failed: %s", exc)


def release_pipeline() -> None:
    """Полностью выгрузить TRELLIS из VRAM (конец subprocess trellis_generate)."""
    global _pipeline, _pipeline_kind
    if _pipeline is None:
        _free_cuda_memory()
        return
    try:
        _release_vram_before_export(_pipeline)
    except Exception as exc:  # noqa: BLE001
        logger.warning("release_pipeline: %s", exc)
        _pipeline = None
        _pipeline_kind = None
        _free_cuda_memory()


def get_pipeline():
    global _pipeline, _pipeline_kind
    if _pipeline is not None:
        _progress("pipeline cache hit — skip load")
        return _pipeline

    import time

    t0 = time.monotonic()
    _ensure_path()
    import torch

    weights = os.getenv("TRELLIS_WEIGHTS", "microsoft/TRELLIS.2-4B")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ver = trellis_version()
    _progress(f"Loading TRELLIS.{ver} device={device} weights={weights} (3–8 мин при первом запуске)")

    if ver in ("2", "trellis2", "trellis.2"):
        try:
            _progress("import Trellis2ImageTo3DPipeline…")
            from trellis2.pipelines import Trellis2ImageTo3DPipeline  # type: ignore

            low_vram = _resolve_low_vram()
            _progress(f"from_pretrained({weights})… смотрите nvidia-smi — растёт VRAM")
            pipe = Trellis2ImageTo3DPipeline.from_pretrained(weights)
            _progress(f"weights loaded in {time.monotonic() - t0:.0f}s, low_vram={low_vram}")
            pipe.low_vram = low_vram
            if device == "cuda" and hasattr(pipe, "cuda"):
                _progress("pipe.cuda()…")
                pipe.cuda()
            elif hasattr(pipe, "to"):
                pipe.to(device)
            _drop_internal_rembg(pipe)
            _pipeline = pipe
            _pipeline_kind = "trellis2_image_to_3d"
            _progress(f"pipeline ready in {time.monotonic() - t0:.0f}s total")
            return _pipeline
        except Exception as exc:
            detail = repr(exc)
            raise ImportError(
                "TRELLIS.2 pipeline load failed. "
                "Build: docker build --build-arg INSTALL_TRELLIS=1 "
                "--build-arg TRELLIS_VERSION=2 -t kwork-worker:trellis2 .\n"
                f"Details: {detail}"
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


def _texture_size_for_task(task_dir: Path) -> int:
    cap = int(os.getenv("TRELLIS2_TEXTURE_SIZE", "1024"))
    if _resolve_low_vram():
        cap = min(cap, 1024)
    meta_path = task_dir / "task_meta.json"
    if meta_path.exists():
        try:
            import json

            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            company_id = int(meta.get("company_id") or 0)
            tier = str(meta.get("tier") or "").lower()
            if company_id > 0 or tier == "large":
                return min(2048, cap) if not _resolve_low_vram() else cap
        except Exception:  # noqa: BLE001
            pass
    return cap


def _release_vram_before_export(pipe) -> None:
    """После inference освободить VRAM перед export GLB (как ComfyUI extract)."""
    global _pipeline, _pipeline_kind
    import gc

    import torch

    if not torch.cuda.is_available():
        return
    try:
        if hasattr(pipe, "to"):
            pipe.to("cpu")
        models = getattr(pipe, "models", None) or {}
        for model in models.values():
            if model is not None and hasattr(model, "cpu"):
                model.cpu()
        for attr in ("image_cond_model", "rembg_model"):
            part = getattr(pipe, attr, None)
            if part is not None and hasattr(part, "cpu"):
                part.cpu()
    except Exception as exc:  # noqa: BLE001
        logger.warning("pipeline offload before export: %s", exc)
    _pipeline = None
    _pipeline_kind = None
    del pipe
    gc.collect()
    torch.cuda.empty_cache()
    if hasattr(torch.cuda, "ipc_collect"):
        torch.cuda.ipc_collect()
    torch.cuda.synchronize()


def _mesh_to_device(mesh, device: str) -> None:
    import torch

    for attr in ("vertices", "faces", "attrs", "coords"):
        val = getattr(mesh, attr, None)
        if isinstance(val, torch.Tensor):
            setattr(mesh, attr, val.detach().to(device))
    vs = getattr(mesh, "voxel_size", None)
    if isinstance(vs, torch.Tensor):
        mesh.voxel_size = vs.to(device)


def _export_trellis2_mesh(mesh, output: Path, *, task_dir: Path | None = None) -> None:
    import torch
    import o_voxel  # type: ignore

    low_vram = _resolve_low_vram()
    export_device = "cuda" if torch.cuda.is_available() else "cpu"
    _mesh_to_device(mesh, export_device)

    skip_simplify = os.getenv("TRELLIS2_SKIP_MESH_SIMPLIFY", "").lower() in ("1", "true", "yes") or low_vram
    if hasattr(mesh, "simplify") and not skip_simplify:
        try:
            mesh.simplify(16_777_216)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TRELLIS.2 mesh.simplify skipped: %s", exc)

    decimation = int(os.getenv("TRELLIS2_DECIMATION", "150000" if low_vram else "300000"))
    texture_size = _texture_size_for_task(task_dir) if task_dir else int(os.getenv("TRELLIS2_TEXTURE_SIZE", "1024"))
    use_webp = os.getenv("TRELLIS2_EXTENSION_WEBP", "0").lower() in ("1", "true", "yes")

    # res из mesh (как app.py grid_size=res), не voxel_shape tensor
    grid_size = getattr(mesh, "res", None)
    if grid_size is None:
        vs = getattr(mesh, "voxel_shape", None)
        if vs is not None and hasattr(vs, "__iter__"):
            try:
                parts = [int(x) for x in vs]
                grid_size = parts[-1] if parts else None
            except Exception:  # noqa: BLE001
                grid_size = None

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
        remesh=not low_vram,
        remesh_band=1,
        remesh_project=0,
        verbose=False,
        **({"grid_size": int(grid_size)} if grid_size else {}),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    glb.export(str(output), extension_webp=use_webp)
    logger.info("TRELLIS.2 export extension_webp=%s texture_size=%s", use_webp, texture_size)


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


def _sampler_params(prefix: str, defaults: dict) -> dict:
    """Параметры sampler из env (как в ComfyUI / app.py TRELLIS.2)."""
    out = dict(defaults)
    steps = os.getenv(f"TRELLIS2_{prefix}_STEPS")
    if steps is not None:
        out["steps"] = int(steps)
    gs = os.getenv(f"TRELLIS2_{prefix}_GUIDANCE")
    if gs is not None:
        out["guidance_strength"] = float(gs)
    gr = os.getenv(f"TRELLIS2_{prefix}_GUIDANCE_RESCALE")
    if gr is not None:
        out["guidance_rescale"] = float(gr)
    rt = os.getenv(f"TRELLIS2_{prefix}_RESCALE_T")
    if rt is not None:
        out["rescale_t"] = float(rt)
    return out


def _pipeline_type_resolved() -> str:
    raw = os.getenv("TRELLIS2_PIPELINE_TYPE", "1024").strip()
    # как в app.py: 1024 → 1024_cascade (лучше качество, как на YouTube)
    if raw == "1024":
        return "1024_cascade"
    if raw == "1536":
        return "1536_cascade"
    return raw


def run_trellis2(task_dir: Path, output: Path) -> Path:
    """TRELLIS.2: image→3D с native PBR (view_00 из photos_nobg)."""
    import torch
    from PIL import Image

    preflight_cuda()
    photos_dir = _require_nobg_dir(task_dir)
    front = _pick_front_image(photos_dir)
    image = Image.open(front).convert("RGBA")
    logger.info("TRELLIS.2 input=%s (single-image, photos_nobg/view_00)", front.name)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    pipe = get_pipeline()
    pipeline_type = _pipeline_type_resolved()
    _progress(f"inference start pipeline_type={pipeline_type} …")
    run_kwargs = {
        "preprocess_image": False,
        "pipeline_type": pipeline_type,
        "tex_slat_sampler_params": _sampler_params(
            "TEX",
            # HF Space defaults (Material Generation)
            {"steps": 12, "guidance_strength": 1.0, "guidance_rescale": 0.0, "rescale_t": 3.0},
        ),
        "shape_slat_sampler_params": _sampler_params(
            "SHAPE",
            # HF Space defaults (Shape Generation)
            {"steps": 12, "guidance_strength": 7.5, "guidance_rescale": 0.5, "rescale_t": 3.0},
        ),
        "sparse_structure_sampler_params": _sampler_params(
            "SS",
            # HF Space defaults (Sparse Structure)
            {"steps": 12, "guidance_strength": 7.5, "guidance_rescale": 0.7, "rescale_t": 5.0},
        ),
    }
    max_tokens = os.getenv("TRELLIS2_MAX_NUM_TOKENS", "").strip()
    if max_tokens:
        run_kwargs["max_num_tokens"] = int(max_tokens)
    logger.info(
        "TRELLIS.2 run pipeline_type=%s tex_steps=%s texture_size=%s",
        pipeline_type,
        run_kwargs["tex_slat_sampler_params"].get("steps"),
        _texture_size_for_task(task_dir),
    )
    meshes = pipe.run(image, **run_kwargs)
    _progress("inference done, export GLB…")
    if not meshes:
        raise RuntimeError("TRELLIS.2 вернул пустой результат")

    _release_vram_before_export(pipe)
    _export_trellis2_mesh(meshes[0], output, task_dir=task_dir)
    if not output.exists() or output.stat().st_size < 1000:
        raise RuntimeError(f"TRELLIS.2 GLB слишком мал: {output}")
    logger.info("TRELLIS.2 → %s (%s bytes)", output, output.stat().st_size)
    release_pipeline()
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
    release_pipeline()
    return output


def run_trellis(task_dir: Path, output: Path) -> Path:
    if trellis_version() in ("2", "trellis2", "trellis.2"):
        preflight_cuda()
        return run_trellis2(task_dir, output)
    return run_trellis_v1(task_dir, output)
