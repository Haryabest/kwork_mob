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

import hashlib
import json
import logging
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Literal

logger = logging.getLogger("trellis_runtime")

_pipeline = None
_pipeline_kind: str | None = None

# Совпадает с backend photos.VIEW_INDICES_BY_COUNT — исходные слоты до expand.
# 3 фото: фронт + лево 90° + право 270° (не 120°/240° — те ближе к тылу и дают дыры на боках).
VIEW_INDICES_BY_COUNT: dict[int, list[int]] = {
    1: [0],
    # Фронт + левый бок 90° + правый бок 270° (раньше [0,4,8] — слабое покрытие боков)
    3: [0, 3, 9],
    5: [0, 2, 4, 6, 8],
    6: [0, 2, 4, 6, 8, 10],
    12: list(range(12)),
}
_VIEW_NAME_RE = re.compile(r"^view_(\d+)", re.IGNORECASE)


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


def _view_index(path: Path) -> int:
    m = _VIEW_NAME_RE.match(path.stem)
    return int(m.group(1)) if m else 10_000


def _file_fingerprint(path: Path) -> bytes:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.digest()


def _photo_count_hint(task_dir: Path | None = None) -> int | None:
    raw = (os.getenv("PHOTO_COUNT") or os.getenv("TASK_PHOTO_COUNT") or "").strip()
    if raw.isdigit():
        return int(raw)
    if task_dir is not None:
        meta_path = task_dir / "task_meta.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                value = meta.get("photo_count")
                if isinstance(value, int) and value > 0:
                    return value
            except Exception:  # noqa: BLE001
                pass
    return None


def _max_views_cap() -> int:
    """Верхний предел. Для multi-photo никогда не режем ниже числа seed-ракурсов."""
    raw = (os.getenv("TRELLIS2_MAX_VIEWS") or "6").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 6


def _list_view_images(photos_dir: Path) -> list[Path]:
    images = sorted(
        (
            p
            for p in photos_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ),
        key=_view_index,
    )
    if not images:
        raise RuntimeError(f"Нет изображений в {photos_dir}")
    return images


def _unique_by_content(images: list[Path]) -> list[Path]:
    """После expand копии одинаковы — оставляем по одному файлу на контент, в порядке view_XX."""
    seen: dict[bytes, Path] = {}
    for path in images:
        fp = _file_fingerprint(path)
        if fp not in seen:
            seen[fp] = path
    return list(seen.values())


def _seed_indices_for_count(photo_count: int | None) -> list[int] | None:
    if photo_count is None:
        return None
    if photo_count in VIEW_INDICES_BY_COUNT:
        return VIEW_INDICES_BY_COUNT[photo_count]
    if photo_count >= 12:
        return list(range(12))
    return None


def pick_input_images(photos_dir: Path, task_dir: Path | None = None) -> list[Path]:
    """
    Входы для TRELLIS.2: все уникальные исходные ракурсы (1/3/5/6/12).

    Важно: TRELLIS2_MAX_VIEWS=1 в старом .env.worker не должен убивать 3-фото заказ
    (иначе снова только view_00 → дыры на боках).
    """
    images = _list_view_images(photos_dir)
    photo_count = _photo_count_hint(task_dir)
    max_cap = _max_views_cap()
    seed_indices = _seed_indices_for_count(photo_count)
    unique = _unique_by_content(images)

    selected: list[Path] = []
    if seed_indices:
        by_idx = {_view_index(p): p for p in images}
        for idx in seed_indices:
            path = by_idx.get(idx)
            if path is not None:
                selected.append(path)
        selected = _unique_by_content(selected)
        # expand-копии / старые слоты [0,4,8] / nobg только front → добираем уникальным контентом
        if len(selected) < min(2, len(unique)):
            selected = unique
    else:
        selected = unique

    if not selected:
        selected = images[:1]

    # Multi-photo: всегда все seed/unique. MAX_VIEWS режет только «лишнее» сверху.
    min_required = len(selected) if (photo_count and photo_count > 1) or len(selected) > 1 else 1
    effective_cap = max(max_cap, min_required) if min_required > 1 else max_cap
    if len(selected) > effective_cap:
        selected = selected[:effective_cap]

    mode = multi_image_mode() if len(selected) > 1 else "single"
    names = ", ".join(p.name for p in selected)
    _progress(
        f"input views={len(selected)} cap={effective_cap}(cfg={max_cap}) "
        f"photo_count={photo_count} multi-image inject mode={mode}: {names}"
    )
    return selected


def _pick_front_image(photos_dir: Path) -> Path:
    return pick_input_images(photos_dir)[0]


def _prepare_multi_cond(cond: dict) -> dict:
    """neg_cond оставляем batch=1, как в TRELLIS v1 run_multi_image."""
    neg = cond.get("neg_cond")
    if neg is not None and hasattr(neg, "shape") and neg.shape[0] > 1:
        cond = {**cond, "neg_cond": neg[:1]}
    return cond


def _synthetic_back_view_enabled(photo_count: int | None, n_views: int) -> bool:
    """3 фото без ракурса 180° — добавляем зеркальный фронт только для геометрии."""
    if os.getenv("TRELLIS2_SYNTHETIC_BACK_VIEW", "1").lower() in ("0", "false", "no"):
        return False
    if photo_count == 3:
        return n_views == 3
    return photo_count is None and n_views == 3


def geometry_view_images(images, task_dir: Path | None = None):
    """
  Возвращает (images_for_geom, added_synthetic_back).
  Текстуру не трогаем — только sparse structure / shape slat.
  """
    from PIL import Image

    n = len(images)
    photo_count = _photo_count_hint(task_dir)
    if not _synthetic_back_view_enabled(photo_count, n):
        return list(images), False
    front = images[0]
    if not isinstance(front, Image.Image):
        return list(images), False
    back = front.transpose(Image.FLIP_LEFT_RIGHT)
    _progress("synthetic back view: mirror front → pseudo 180° for geometry (3-photo)")
    return [*images, back], True


@contextmanager
def inject_sampler_multi_image(
    sampler,
    num_images: int,
    mode: Literal["stochastic", "multidiffusion"] = "stochastic",
) -> Iterator[None]:
    """
    Multi-view conditioning без смены num_samples.
    Stochastic: цикл по view на denoising-шагах.
    Multidiffusion: усреднение предсказаний всех view (лучше для боков).
    """
    if num_images <= 1:
        yield
        return

    import torch

    old = sampler._inference_model
    step_i = [0]

    def _slice_cond(cond, idx: int):
        if torch.is_tensor(cond) and cond.shape[0] > 1:
            return cond[idx : idx + 1]
        return cond

    if mode == "stochastic":

        def _new_inference_model(self, model, x_t, t, cond, *args, **kwargs):
            idx = step_i[0] % num_images
            step_i[0] += 1
            return old(model, x_t, t, _slice_cond(cond, idx), *args, **kwargs)

    elif mode == "multidiffusion":

        def _new_inference_model(self, model, x_t, t, cond, *args, **kwargs):
            if not (torch.is_tensor(cond) and cond.shape[0] > 1):
                return old(model, x_t, t, cond, *args, **kwargs)
            # Усредняем только «позитивную» ветку: для каждого view полный CFG с общим neg_cond.
            preds = [
                old(model, x_t, t, cond[i : i + 1], *args, **kwargs)
                for i in range(cond.shape[0])
            ]
            out = preds[0]
            for p in preds[1:]:
                out = out + p
            return out / len(preds)

    else:
        raise ValueError(f"Unsupported multi-image mode: {mode}")

    sampler._inference_model = _new_inference_model.__get__(sampler, type(sampler))
    try:
        _progress(f"multi-image inject mode={mode} views={num_images}")
        yield
    finally:
        sampler._inference_model = old


def _normalize_multi_mode(raw: str, default: str) -> Literal["stochastic", "multidiffusion"]:
    value = (raw or "").strip().lower() or default
    if value in ("stochastic", "cycle", "stoch", "round_robin"):
        return "stochastic"
    return "multidiffusion"


def multi_image_mode(stage: str = "geometry") -> Literal["stochastic", "multidiffusion"]:
    """
    Геометрия: multidiffusion — бока/лево стабильны (stochastic даёт дыры на боках).
    Текстура: multidiffusion — без швов между ракурсами.
    Тыл при 3 фото не снимается — дыры сзади закрываем prefill/remesh на export.
    """
    if stage == "texture":
        return _normalize_multi_mode(
            os.getenv("TRELLIS2_MULTI_IMAGE_MODE_TEX") or "", "multidiffusion"
        )
    return _normalize_multi_mode(os.getenv("TRELLIS2_MULTI_IMAGE_MODE") or "", "multidiffusion")


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
    """TRELLIS.2: входы из photos_nobg после remove_background (§6.2)."""
    photos_nobg = task_dir / "photos_nobg"
    if not photos_nobg.is_dir() or not any(photos_nobg.iterdir()):
        raise RuntimeError(
            "TRELLIS.2 требует photos_nobg/* — сначала выполните remove_background.py"
        )
    return photos_nobg


def _resolve_attn_backend() -> str:
    """Dense attention: sdpa. Sparse Slat (shape/tex): только xformers/flash_attn — sdpa → xformers."""
    backend = (os.getenv("ATTN_BACKEND") or "xformers").strip().lower()
    if backend == "sdpa":
        try:
            import xformers  # noqa: F401

            _progress("ATTN_BACKEND=sdpa: sparse TRELLIS.2 → xformers (sdpa нет для shape Slat)")
            backend = "xformers"
        except ImportError:
            _progress("ATTN_BACKEND=sdpa, xformers нет — dense=sdpa, sparse может упасть на flash_attn")
    elif backend == "flash_attn":
        try:
            import flash_attn  # noqa: F401
        except ImportError:
            backend = "xformers"
            _progress("flash_attn не установлен → ATTN_BACKEND=xformers")
    elif backend == "xformers":
        try:
            import xformers  # noqa: F401
        except ImportError:
            backend = "sdpa"
            _progress("xformers не установлен → ATTN_BACKEND=sdpa")
    os.environ["ATTN_BACKEND"] = backend
    os.environ["SPARSE_ATTN_BACKEND"] = backend
    return backend


def _sync_trellis_attn_modules(backend: str) -> None:
    """Перезаписать backend после импорта trellis2 (sparse по умолчанию flash_attn)."""
    sparse_backend = backend
    if sparse_backend == "sdpa":
        sparse_backend = "xformers"
    for mod_path, attr, value in (
        ("trellis2.modules.sparse.config", "ATTN", sparse_backend),
        ("trellis2.modules.attention.config", "BACKEND", backend),
    ):
        try:
            mod = __import__(mod_path, fromlist=["_"])
            setattr(mod, attr, value)
        except Exception:  # noqa: BLE001
            pass


def _resolve_low_vram() -> bool:
    auto = True
    try:
        import torch

        if torch.cuda.is_available():
            gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            auto = gb < 20.0
    except Exception:  # noqa: BLE001
        auto = True

    raw = os.getenv("TRELLIS2_LOW_VRAM")
    if raw is None:
        return auto
    explicit = str(raw).strip().lower() in ("1", "true", "yes")
    if not explicit and auto:
        _progress(
            "TRELLIS2_LOW_VRAM=0, но GPU <20GB — принудительно low_vram=True "
            "(иначе OOM на pipe.cuda)"
        )
        return True
    return explicit


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


def _enable_hf_download_logs() -> None:
    import logging

    for name in ("huggingface_hub", "huggingface_hub.file_download"):
        logging.getLogger(name).setLevel(logging.INFO)
    try:
        from huggingface_hub.utils import enable_progress_bars

        enable_progress_bars()
    except Exception:  # noqa: BLE001
        pass


def get_pipeline():
    global _pipeline, _pipeline_kind
    if _pipeline is not None:
        _progress("pipeline cache hit — skip load")
        return _pipeline

    import time

    t0 = time.monotonic()
    _ensure_path()
    attn = _resolve_attn_backend()
    import torch

    weights = os.getenv("TRELLIS_WEIGHTS", "microsoft/TRELLIS.2-4B")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ver = trellis_version()
    _progress(f"Loading TRELLIS.{ver} device={device} weights={weights} (3–8 мин при первом запуске)")

    if ver in ("2", "trellis2", "trellis.2"):
        try:
            _progress("import Trellis2ImageTo3DPipeline…")
            from trellis2.pipelines import Trellis2ImageTo3DPipeline  # type: ignore

            _sync_trellis_attn_modules(attn)

            try:
                from dinov3_local import apply_local_dinov3_patch

                if apply_local_dinov3_patch():
                    _progress("DINOv3: локальные веса (без gated HF)")
            except Exception as exc:  # noqa: BLE001
                logger.warning("dinov3 local patch: %s", exc)

            low_vram = _resolve_low_vram()
            _enable_hf_download_logs()
            _progress(
                "from_pretrained: скачивание недостающих .safetensors (последний часто "
                "slat_flow_imgshape2tex_1024, ~3–6 ГБ) — смотрите du -sh ~/hf_cache"
            )
            _progress(f"from_pretrained({weights})… смотрите nvidia-smi — растёт VRAM")
            pipe = Trellis2ImageTo3DPipeline.from_pretrained(weights)
            _progress(f"weights loaded in {time.monotonic() - t0:.0f}s, low_vram={low_vram}")
            pipe.low_vram = low_vram
            _drop_internal_rembg(pipe)
            _free_cuda_memory()
            if device == "cuda" and hasattr(pipe, "cuda"):
                _progress(f"pipe.cuda()… low_vram={low_vram}")
                pipe.cuda()
            elif hasattr(pipe, "to"):
                pipe.to(device)
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
    from pipeline_env import max_quality_mode

    if max_quality_mode():
        raw = os.getenv("TRELLIS2_TEXTURE_SIZE", "2048").strip()
        try:
            return int(raw)
        except ValueError:
            return 2048
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


def _trim_vram_before_decode(pipe) -> None:
    """После texture slat: только tex flow off GPU (decoders для decode_latent не трогаем)."""
    import gc

    import torch

    for attr in ("image_cond_model", "rembg_model"):
        part = getattr(pipe, attr, None)
        if part is not None and hasattr(part, "cpu"):
            try:
                part.cpu()
            except Exception:  # noqa: BLE001
                pass
        setattr(pipe, attr, None)
    models = getattr(pipe, "models", None)
    if isinstance(models, dict):
        for key in list(models.keys()):
            if "tex_slat_flow" not in key:
                continue
            model = models.pop(key, None)
            if model is not None and hasattr(model, "cpu"):
                try:
                    model.cpu()
                except Exception:  # noqa: BLE001
                    pass
            del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        if hasattr(torch.cuda, "ipc_collect"):
            torch.cuda.ipc_collect()


def _mesh_to_device(mesh, device: str) -> None:
    import torch

    for attr in ("vertices", "faces", "attrs", "coords", "voxel_size"):
        val = getattr(mesh, attr, None)
        if isinstance(val, torch.Tensor):
            setattr(mesh, attr, val.detach().to(device))
    layout = getattr(mesh, "layout", None)
    if isinstance(layout, dict):
        for key, val in layout.items():
            if isinstance(val, torch.Tensor):
                layout[key] = val.detach().to(device)


def _mesh_to_cpu(mesh) -> None:
    _mesh_to_device(mesh, "cpu")


def _export_hole_perimeter() -> float:
    """to_glb внутри o_voxel хардкодит 3e-2 — крупные дыры (3-фото) не закрываются."""
    raw = (os.getenv("TRELLIS2_MAX_HOLE_PERIMETER") or "1.0").strip()
    try:
        return max(0.25, float(raw))
    except ValueError:
        return 1.0


def _cumesh_fill_stages(mesh, peri: float, orig_fill) -> None:
    """Только зашивка — без remove_small (иначе съедает боковые фрагменты)."""
    for stage in (peri * 0.4, peri, min(2.0, peri * 1.5)):
        try:
            orig_fill(mesh, max_hole_perimeter=max(3e-2, stage))
        except TypeError:
            try:
                orig_fill(mesh)
            except Exception:  # noqa: BLE001
                pass
            break
        except Exception:  # noqa: BLE001
            break


def _cumesh_cleanup(mesh, peri: float, orig_fill) -> None:
    """Полная чистка после remesh/simplify в to_glb."""
    for name, args in (
        ("remove_duplicate_faces", ()),
        ("repair_non_manifold_edges", ()),
    ):
        fn = getattr(mesh, name, None)
        if fn is None:
            continue
        try:
            fn(*args)
        except Exception:  # noqa: BLE001
            pass
    if os.getenv("TRELLIS2_REMOVE_SMALL_COMPONENTS", "1").lower() in ("1", "true", "yes"):
        fn = getattr(mesh, "remove_small_connected_components", None)
        if fn is not None:
            try:
                fn(1e-5)
            except Exception:  # noqa: BLE001
                pass
    _cumesh_fill_stages(mesh, peri, orig_fill)
    unify = getattr(mesh, "unify_face_orientations", None)
    if unify is not None:
        try:
            unify()
        except Exception:  # noqa: BLE001
            pass


def cumesh_prefill_holes(vertices, faces, peri: float):
    """
    Зашивка до to_glb: строим CuMesh сами и чистим топологию.
    Не зависит от monkey-patch (cumesh — C-расширение, подмена методов может быть запрещена).
    Возвращает (vertices, faces) — исходные при любой ошибке.
    """
    try:
        import cumesh
    except Exception as exc:  # noqa: BLE001
        _progress(f"prefill skipped: cumesh недоступен ({exc})")
        return vertices, faces
    cls = getattr(cumesh, "CuMesh", None)
    if cls is None:
        _progress("prefill skipped: cumesh.CuMesh отсутствует")
        return vertices, faces
    try:
        mesh = cls()
        mesh.init(vertices, faces)
        before = int(getattr(mesh, "num_faces", 0) or 0)
        _cumesh_fill_stages(mesh, peri, cls.fill_holes)
        after = int(getattr(mesh, "num_faces", 0) or 0)
        new_v, new_f = mesh.read()
        _progress(f"prefill holes peri={peri:.2f} faces {before} → {after}")
        return new_v, new_f
    except Exception as exc:  # noqa: BLE001
        logger.warning("cumesh prefill failed: %s", exc)
        _progress(f"prefill failed ({exc}) — экспорт из исходного меша")
        return vertices, faces


@contextmanager
def _patch_cumesh_holes(peri: float):
    """
    to_glb: max_hole_perimeter захардкожен 3e-2, а ветка remesh=True после
    dual contouring делает только simplify() — без зашивки и cleanup.
    Патчим fill_holes (перим.) и simplify (cleanup после), чтобы дыр не оставалось.
    """
    try:
        import cumesh
    except Exception:  # noqa: BLE001
        yield
        return
    cls = getattr(cumesh, "CuMesh", None)
    if cls is None or not hasattr(cls, "fill_holes"):
        yield
        return
    orig_fill = cls.fill_holes
    orig_simplify = getattr(cls, "simplify", None)

    def _patched_fill(self, *args, **kwargs):
        if args:
            try:
                cur = float(args[0])
            except (TypeError, ValueError):
                cur = 0.0
            if cur < peri:
                args = (peri,) + args[1:]
        else:
            raw = kwargs.get("max_hole_perimeter")
            try:
                cur = float(raw) if raw is not None else 0.0
            except (TypeError, ValueError):
                cur = 0.0
            if cur < peri:
                kwargs["max_hole_perimeter"] = peri
        try:
            return orig_fill(self, *args, **kwargs)
        except TypeError:
            return orig_fill(self)

    def _patched_simplify(self, *args, **kwargs):
        result = orig_simplify(self, *args, **kwargs)
        _cumesh_cleanup(self, peri, orig_fill)
        return result

    # pybind11-типы запрещают подмену атрибутов — тогда работает только prefill.
    patched = False
    try:
        cls.fill_holes = _patched_fill
        if orig_simplify is not None:
            cls.simplify = _patched_simplify
        patched = True
    except (AttributeError, TypeError) as exc:
        _progress(f"to_glb hole patch НЕ применён ({exc}) — зашивка только prefill")
    try:
        if patched:
            _progress(f"to_glb hole patch: perimeter={peri:.3f}, cleanup after simplify")
        yield
    finally:
        if patched:
            cls.fill_holes = orig_fill
            if orig_simplify is not None:
                cls.simplify = orig_simplify


def _call_to_glb(o_voxel, to_glb_kw: dict):
    peri = _export_hole_perimeter()
    # Форки ComfyUI принимают fill_holes_perimeter; stock microsoft — нет (TypeError → clean).
    kw = {**to_glb_kw, "fill_holes_perimeter": peri}
    with _patch_cumesh_holes(peri):
        try:
            return o_voxel.postprocess.to_glb(**kw)
        except TypeError as exc:
            if "unexpected keyword" not in str(exc):
                raise
            drop = {
                "remove_floaters",
                "remove_inner_faces",
                "dual_contouring_resolution",
                "fill_holes_perimeter",
            }
            clean = {k: v for k, v in kw.items() if k not in drop}
            logger.warning("TRELLIS.2 to_glb fallback: %s", exc)
            return o_voxel.postprocess.to_glb(**clean)


def _cuda_vram_gb() -> float | None:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    except Exception:  # noqa: BLE001
        pass
    return None


def _cap_decimation(decimation: int, low_vram: bool, grid_size: int | None) -> int:
    from pipeline_env import max_quality_mode

    if max_quality_mode():
        return decimation
    cap = decimation
    vram = _cuda_vram_gb()
    if low_vram or (vram is not None and vram <= 18):
        cap = min(cap, int(os.getenv("TRELLIS2_DECIMATION_VRAM_CAP", "300000")))
    if grid_size and int(grid_size) > 1024:
        cap = min(cap, int(os.getenv("TRELLIS2_DECIMATION_LARGE_GRID_CAP", "300000")))
    if cap < decimation:
        logger.info("TRELLIS.2 decimation capped %s → %s (16GB VRAM / grid)", decimation, cap)
        _progress(f"decimation capped {decimation} → {cap} (VRAM)")
    return cap


def _resolve_remesh_enabled(export_device: str) -> bool:
    from pipeline_env import max_quality_mode

    if export_device == "cpu":
        return False
    raw = (os.getenv("TRELLIS2_REMESH") or "").strip().lower()
    if max_quality_mode():
        # remesh=False → дыры и «осколки» voxel mesh; ComfyUI всегда remesh при export
        if raw in ("0", "false", "no"):
            logger.warning("max quality: TRELLIS2_REMESH=0 ignored — remesh required for solid mesh")
        return True
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    vram = _cuda_vram_gb()
    return vram is not None and vram > 20


def _is_cuda_oom(exc: BaseException) -> bool:
    err = str(exc).lower()
    return "out of memory" in err or ("cuda" in err and "error" in err)


def _export_trellis2_mesh(mesh, output: Path, *, task_dir: Path | None = None) -> None:
    import torch
    import o_voxel  # type: ignore

    low_vram = _resolve_low_vram()
    prefer_cpu = os.getenv("TRELLIS2_EXPORT_CPU", "0").lower() in ("1", "true", "yes")
    # После offload пайплайна remesh/to_glb обычно нужен CUDA; CPU-only ломает remesh (mixed devices).
    if torch.cuda.is_available() and not prefer_cpu:
        export_device = "cuda"
        _mesh_to_device(mesh, "cuda")
        _free_cuda_memory()
        _progress("export GLB on CUDA (pipeline VRAM freed)")
    else:
        export_device = "cpu"
        _mesh_to_cpu(mesh)
        _free_cuda_memory()
        _progress("export GLB on CPU — remesh может быть отключён")

    skip_simplify = os.getenv("TRELLIS2_SKIP_MESH_SIMPLIFY", "").lower() in ("1", "true", "yes")
    simplify_method = (os.getenv("TRELLIS2_SIMPLIFY_METHOD") or "cumesh").strip().lower()
    if hasattr(mesh, "simplify") and not skip_simplify and simplify_method != "cumesh":
        try:
            mesh.simplify(16_777_216)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TRELLIS.2 mesh.simplify skipped: %s", exc)

    decimation_raw = (
        os.getenv("TRELLIS2_SIMPLIFY_TARGET_FACES")
        or os.getenv("TRELLIS2_DECIMATION")
        or ("150000" if low_vram else "1000000")
    )
    decimation = int(decimation_raw)

    grid_size = getattr(mesh, "res", None)
    if grid_size is None:
        vs = getattr(mesh, "voxel_shape", None)
        if vs is not None and hasattr(vs, "__iter__"):
            try:
                parts = [int(x) for x in vs]
                grid_size = parts[-1] if parts else None
            except Exception:  # noqa: BLE001
                grid_size = None

    from pipeline_env import max_quality_mode

    if not max_quality_mode():
        decimation = _cap_decimation(decimation, low_vram, int(grid_size) if grid_size else None)

    reconstruct_res = (os.getenv("TRELLIS2_RECONSTRUCT_RESOLUTION") or "").strip()
    if max_quality_mode():
        texture_size = max(2048, int(os.getenv("TRELLIS2_TEXTURE_SIZE", "2048")))
    elif task_dir:
        texture_size = _texture_size_for_task(task_dir)
    else:
        texture_size = int(os.getenv("TRELLIS2_TEXTURE_SIZE", reconstruct_res or "1024"))
    if reconstruct_res and not max_quality_mode():
        try:
            texture_size = int(reconstruct_res)
        except ValueError:
            pass
    if low_vram and not max_quality_mode():
        texture_size = min(texture_size, int(os.getenv("TRELLIS2_EXPORT_TEXTURE_MAX", "1024")))
    use_webp = (
        not max_quality_mode()
        and os.getenv("TRELLIS2_EXTENSION_WEBP", "0").lower() in ("1", "true", "yes")
    )

    # band=3: шире полоса DC — мостит разрывы на тыле (3 фото без ракурса 180°)
    remesh_band = float(os.getenv("TRELLIS2_REMESH_BAND", "3"))
    remesh_project = float(os.getenv("TRELLIS2_REMESH_PROJECT", "0.9"))
    remesh_enabled = _resolve_remesh_enabled(export_device)
    if export_device == "cpu" and remesh_enabled:
        remesh_enabled = False
        logger.info("TRELLIS.2 CPU export: remesh disabled (o_voxel needs CUDA)")

    export_vertices, export_faces = mesh.vertices, mesh.faces
    if export_device == "cuda" and os.getenv("TRELLIS2_PREFILL_HOLES", "1").lower() in (
        "1",
        "true",
        "yes",
    ):
        export_vertices, export_faces = cumesh_prefill_holes(
            export_vertices, export_faces, _export_hole_perimeter()
        )

    to_glb_kw: dict = {
        "vertices": export_vertices,
        "faces": export_faces,
        "attr_volume": mesh.attrs,
        "coords": mesh.coords,
        "attr_layout": mesh.layout,
        "voxel_size": mesh.voxel_size,
        "aabb": [[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        "decimation_target": decimation,
        "texture_size": texture_size,
        "remesh": remesh_enabled,
        "remesh_band": remesh_band,
        "remesh_project": remesh_project,
        "verbose": os.getenv("TRELLIS2_VERBOSE", "0").lower() in ("1", "true", "yes"),
    }
    if grid_size:
        to_glb_kw["grid_size"] = int(grid_size)
    # remove_floaters / inner faces — Comfy mesh cleanup (TypeError fallback in _call_to_glb)
    if os.getenv("TRELLIS2_REMOVE_FLOATERS", "1").lower() in ("1", "true", "yes"):
        to_glb_kw["remove_floaters"] = True
    if os.getenv("TRELLIS2_REMOVE_INNER_FACES", "1").lower() in ("1", "true", "yes"):
        to_glb_kw["remove_inner_faces"] = True
    if os.getenv("TRELLIS2_O_VOXEL_EXTENDED", "0").lower() in ("1", "true", "yes"):
        dual = (os.getenv("TRELLIS2_DUAL_CONTURING_RESOLUTION") or "").strip().lower()
        if dual and dual != "auto":
            try:
                to_glb_kw["dual_contouring_resolution"] = int(dual)
            except ValueError:
                pass

    _progress(
        f"export config max_quality={max_quality_mode()} "
        f"decimation={decimation} texture={texture_size} remesh={remesh_enabled}"
    )

    def _run_to_glb(kw: dict):
        import threading
        import time as _time

        _progress(
            f"to_glb start remesh={kw.get('remesh')} decimation={kw.get('decimation_target')} "
            f"texture={kw.get('texture_size')} grid={kw.get('grid_size') or grid_size or 'auto'}"
        )
        t0 = _time.monotonic()
        done = False

        def _export_heartbeat() -> None:
            while not done:
                _time.sleep(30)
                if not done:
                    _progress(f"to_glb still running ({int(_time.monotonic() - t0)}s)…")

        hb = threading.Thread(target=_export_heartbeat, daemon=True)
        hb.start()
        try:
            result = _call_to_glb(o_voxel, kw)
        finally:
            done = True
        _progress(f"to_glb done in {int(_time.monotonic() - t0)}s")
        return result

    glb = None
    try:
        glb = _run_to_glb(to_glb_kw)
    except RuntimeError as exc:
        if _is_cuda_oom(exc):
            _free_cuda_memory()
            if max_quality_mode():
                fallbacks = [
                    {
                        **to_glb_kw,
                        "decimation_target": min(decimation, 200000),
                    },
                    {
                        **to_glb_kw,
                        "decimation_target": min(decimation, 150000),
                    },
                    {**to_glb_kw, "remesh": False},
                ]
            else:
                fallbacks = [
                    {**to_glb_kw, "remesh": False, "decimation_target": min(decimation, 300000)},
                    {**to_glb_kw, "remesh": False, "decimation_target": 150000},
                ]
            for fb in fallbacks:
                try:
                    logger.warning(
                        "TRELLIS.2 OOM retry: remesh=%s decimation=%s",
                        fb["remesh"],
                        fb["decimation_target"],
                    )
                    _progress(
                        f"OOM retry remesh={fb['remesh']} decimation={fb['decimation_target']}"
                    )
                    glb = _run_to_glb(fb)
                    if not fb.get("remesh", True):
                        _progress("export fallback remesh=False — mesh может иметь дыры")
                    break
                except RuntimeError as retry_exc:
                    if not _is_cuda_oom(retry_exc):
                        raise
                    _free_cuda_memory()
            if glb is None:
                hint = (
                    "16GB VRAM: уменьшите TRELLIS2_DECIMATION (200000) или TRELLIS2_TEXTURE_SIZE"
                    if max_quality_mode()
                    else ""
                )
                raise RuntimeError(f"TRELLIS.2 export OOM after retries: {exc}. {hint}") from exc
        elif export_device == "cpu" and torch.cuda.is_available() and "device" in str(exc).lower():
            logger.warning("TRELLIS.2 CPU export device error, retry CUDA: %s", exc)
            _mesh_to_device(mesh, "cuda")
            to_glb_kw["remesh"] = os.getenv("TRELLIS2_REMESH", "1").lower() in ("1", "true", "yes")
            glb = _run_to_glb(to_glb_kw)
        else:
            raise
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


_SAMPLER_PARAM_KEYS = frozenset(
    {
        "steps",
        "guidance_strength",
        "guidance_rescale",
        "rescale_t",
        "guidance_interval",
        "downsampling",
    }
)


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
    gis = os.getenv(f"TRELLIS2_{prefix}_GUIDANCE_INTERVAL_START")
    gie = os.getenv(f"TRELLIS2_{prefix}_GUIDANCE_INTERVAL_END")
    if gis is not None:
        out["guidance_interval"] = (float(gis), float(gie or "1.0"))
    return {k: v for k, v in out.items() if k in _SAMPLER_PARAM_KEYS}


def _pipeline_type_resolved() -> str:
    raw = os.getenv("TRELLIS2_PIPELINE_TYPE", "1024_cascade").strip()
    staged = os.getenv("TRELLIS_STAGED_PIPELINE", "1").lower() in ("1", "true", "yes")
    if staged:
        if raw == "1024":
            return "1024_cascade"
        if raw == "1536":
            return "1536_cascade"
        return raw
    if raw == "1024":
        return "1024_cascade"
    if raw == "1536":
        return "1536_cascade"
    return raw


def run_trellis2(task_dir: Path, output: Path) -> Path:
    """TRELLIS.2: image→3D с native PBR (1+ уникальных view из photos_nobg)."""
    import torch
    from PIL import Image

    preflight_cuda()
    attn = _resolve_attn_backend()
    _sync_trellis_attn_modules(attn)
    photos_dir = _require_nobg_dir(task_dir)
    paths = pick_input_images(photos_dir, task_dir=task_dir)
    images = [Image.open(p).convert("RGBA") for p in paths]
    logger.info(
        "TRELLIS.2 inputs=%s (%s-image)",
        ",".join(p.name for p in paths),
        len(images),
    )

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    pipe = get_pipeline()
    pipeline_type = _pipeline_type_resolved()
    _progress(f"inference start pipeline_type={pipeline_type} views={len(images)} …")

    if len(images) == 1:
        run_kwargs = {
            "preprocess_image": False,
            "pipeline_type": pipeline_type,
            "tex_slat_sampler_params": _sampler_params(
                "TEX",
                {"steps": 12, "guidance_strength": 1.0, "guidance_rescale": 0.0, "rescale_t": 3.0},
            ),
            "shape_slat_sampler_params": _sampler_params(
                "SHAPE",
                {"steps": 12, "guidance_strength": 7.5, "guidance_rescale": 0.5, "rescale_t": 3.0},
            ),
            "sparse_structure_sampler_params": _sampler_params(
                "SS",
                {"steps": 12, "guidance_strength": 7.5, "guidance_rescale": 0.7, "rescale_t": 5.0},
            ),
        }
        max_tokens = os.getenv("TRELLIS2_MAX_NUM_TOKENS", "").strip()
        if max_tokens:
            run_kwargs["max_num_tokens"] = int(max_tokens)
        meshes = pipe.run(images[0], **run_kwargs)
    else:
        # Multi-view: get_cond(B=N) + sampler injection; num_samples остаётся 1.
        from trellis_staged import run_comfy_staged

        return run_comfy_staged(task_dir, output)

    _progress("inference done, offload mesh + free pipeline VRAM…")
    if not meshes:
        raise RuntimeError("TRELLIS.2 вернул пустой результат")

    mesh = meshes[0]
    _release_vram_before_export(pipe)
    _free_cuda_memory()
    try:
        from trellis_mesh_ops import apply_pre_export_ops

        apply_pre_export_ops(mesh)
    except Exception as exc:  # noqa: BLE001
        logger.warning("TRELLIS.2 pre-export ops skipped: %s", exc)
    _mesh_to_cpu(mesh)
    _progress("export GLB…")
    _export_trellis2_mesh(mesh, output, task_dir=task_dir)
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
