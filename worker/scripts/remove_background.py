"""Удаление фона: briaai/RMBG-2.0 (primary) + legacy DeepLab/SAM fallback."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_rmbg2_model = None
_sam_predictor = None
_deeplab_model = None


def _nobg_engine() -> str:
    return (os.getenv("NOBG_ENGINE", "rmbg2") or "rmbg2").strip().lower()


def _view00_only() -> bool:
    raw = (os.getenv("NOBG_VIEW00_ONLY") or "").strip().lower()
    if raw in ("1", "true", "yes", "0", "false", "no"):
        return raw in ("1", "true", "yes")
    ver = (os.getenv("TRELLIS_VERSION") or "2").strip().lower()
    return ver in ("2", "trellis2", "trellis.2")


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


# Исходные слоты до expand — как backend photos.VIEW_INDICES_BY_COUNT.
_VIEW_INDICES_BY_COUNT: dict[int, list[int]] = {
    1: [0],
    3: [0, 3, 9],
    5: [0, 2, 4, 6, 8],
    6: [0, 2, 4, 6, 8, 10],
    12: list(range(12)),
}


def _mask_ratio(mask: np.ndarray) -> float:
    m = mask.astype(bool)
    if m.size == 0:
        return 0.0
    return float(m.mean())


def _rmbg_mask_threshold() -> int:
    raw_sens = (os.getenv("NOBG_SENSITIVITY") or "").strip()
    if raw_sens:
        try:
            sens = float(raw_sens)
            return max(0, min(255, int(round(255 * (1.0 - sens)))))
        except ValueError:
            pass
    return int(os.getenv("NOBG_MASK_THRESHOLD", "128"))


def _postprocess_rmbg_mask(mask: np.ndarray) -> np.ndarray:
    """ComfyUI RMBG-2.0: blur, offset, invert."""
    blur = int(os.getenv("NOBG_MASK_BLUR", "0"))
    offset = int(os.getenv("NOBG_MASK_OFFSET", "0"))
    invert = os.getenv("NOBG_INVERT_OUTPUT", "0").lower() in ("1", "true", "yes")
    out = mask.astype(np.uint8)
    if blur > 0:
        from PIL import ImageFilter

        out = np.array(Image.fromarray(out).filter(ImageFilter.GaussianBlur(radius=blur)))
    if offset != 0:
        try:
            import cv2  # type: ignore

            k = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (abs(offset) * 2 + 1, abs(offset) * 2 + 1),
            )
            op = cv2.MORPH_DILATE if offset > 0 else cv2.MORPH_ERODE
            out = cv2.morphologyEx(out, op, k)
        except Exception:  # noqa: BLE001
            pass
    if invert:
        out = 255 - out
    return out


def _apply_alpha_rgba(img: Image.Image, alpha: np.ndarray) -> Image.Image:
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    a = np.clip(alpha, 0.0, 1.0)
    arr[:, :, 3] = (a * 255.0).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _mask_metrics_alpha(alpha: np.ndarray) -> dict:
    a = np.clip(alpha, 0.0, 1.0)
    fg = a > 0.05
    if not np.any(fg):
        return {
            "ratio": 0.0,
            "height_frac": 0.0,
            "width_frac": 0.0,
            "coverage_ok": False,
        }
    h, w = a.shape[:2]
    ys, xs = np.where(fg)
    height_frac = (ys.max() - ys.min() + 1) / max(h, 1)
    width_frac = (xs.max() - xs.min() + 1) / max(w, 1)
    ratio = float(fg.mean())
    min_h = float(os.getenv("NOBG_MIN_HEIGHT_FRAC", "0.45"))
    min_w = float(os.getenv("NOBG_MIN_WIDTH_FRAC", "0.22"))
    min_r = float(os.getenv("NOBG_MIN_RATIO", "0.05"))
    coverage_ok = height_frac >= min_h and width_frac >= min_w and ratio >= min_r
    return {
        "ratio": ratio,
        "height_frac": round(height_frac, 4),
        "width_frac": round(width_frac, 4),
        "coverage_ok": coverage_ok,
    }


def _apply_mask_rgba(img: Image.Image, mask: np.ndarray) -> Image.Image:
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    m = (mask > 0).astype(np.uint8) * 255
    arr[:, :, 3] = m
    return Image.fromarray(arr, "RGBA")


def _mask_metrics(mask: np.ndarray) -> dict:
    fg = mask > 10 if mask.dtype != np.uint8 or mask.max() > 1 else mask.astype(bool)
    if not np.any(fg):
        return {
            "ratio": 0.0,
            "height_frac": 0.0,
            "width_frac": 0.0,
            "coverage_ok": False,
        }
    ys, xs = np.where(fg)
    h, w = fg.shape[:2]
    height_frac = (ys.max() - ys.min() + 1) / max(h, 1)
    width_frac = (xs.max() - xs.min() + 1) / max(w, 1)
    ratio = float(fg.mean())
    min_h = float(os.getenv("NOBG_MIN_HEIGHT_FRAC", "0.45"))
    min_w = float(os.getenv("NOBG_MIN_WIDTH_FRAC", "0.22"))
    coverage_ok = height_frac >= min_h and width_frac >= min_w and ratio >= float(
        os.getenv("NOBG_MIN_RATIO", "0.10")
    )
    return {
        "ratio": ratio,
        "height_frac": round(height_frac, 4),
        "width_frac": round(width_frac, 4),
        "coverage_ok": coverage_ok,
    }


def _alpha_from_rgba(im: Image.Image) -> np.ndarray:
    return np.array(im.convert("RGBA"))[:, :, 3]


def _release_rmbg2() -> None:
    global _rmbg2_model
    if _rmbg2_model is None:
        return
    try:
        import torch

        model, _device = _rmbg2_model
        del model
        _rmbg2_model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("[remove_background] RMBG-2.0 VRAM released", flush=True)
    except Exception:  # noqa: BLE001
        _rmbg2_model = None


def warmup_nobg() -> None:
    """Загрузить nobg-модель в GPU и освободить VRAM (кэш весов + ядра)."""
    if _nobg_engine() == "legacy":
        return
    _get_rmbg2()
    _release_rmbg2()


def _get_rmbg2():
    global _rmbg2_model
    if _rmbg2_model is not None:
        return _rmbg2_model
    try:
        import torch
        from transformers import AutoModelForImageSegmentation
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] RMBG-2.0 import failed: {exc}")
        return None
    model_id = (os.getenv("NOBG_MODEL_ID") or "briaai/RMBG-2.0").strip()
    token = (os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN") or "").strip() or None
    try:
        torch.set_float32_matmul_precision("high")
        model = AutoModelForImageSegmentation.from_pretrained(
            model_id,
            trust_remote_code=True,
            token=token,
        )
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        _rmbg2_model = (model, device)
        print(f"[remove_background] RMBG-2.0 loaded ({model_id}) device={device}")
        return _rmbg2_model
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] RMBG-2.0 load failed: {exc}")
        return None


def _rmbg2_remove(img: Image.Image) -> tuple[Image.Image, float, float, dict] | None:
    loaded = _get_rmbg2()
    if loaded is None:
        return None
    model, device = loaded
    try:
        import torch
        from torchvision import transforms

        size = int(os.getenv("NOBG_INPUT_SIZE", "1024"))
        rgb = img.convert("RGB")
        transform_image = transforms.Compose(
            [
                transforms.Resize((size, size)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )
        input_tensor = transform_image(rgb).unsqueeze(0).to(device)
        with torch.no_grad():
            preds = model(input_tensor)[-1].sigmoid().cpu()
        pred = preds[0].squeeze().numpy()
        sens = float(os.getenv("NOBG_SENSITIVITY", "1.0"))
        # ComfyUI RMBG-2.0: soft alpha, sensitivity как множитель
        from PIL import Image as PILImage

        alpha_small = np.clip(pred * sens, 0.0, 1.0)
        alpha_u8 = (alpha_small * 255.0).astype(np.uint8)
        alpha = np.array(
            PILImage.fromarray(alpha_u8).resize(rgb.size, PILImage.BILINEAR)
        ) / 255.0
        alpha = np.clip(alpha, 0.0, 1.0)
        if os.getenv("NOBG_REFINE_FOREGROUND", "0").lower() in ("1", "true", "yes"):
            try:
                from rembg import remove

                refined = remove(rgb, only_mask=True)
                if isinstance(refined, Image.Image):
                    alpha = np.clip(np.array(refined.convert("L")) / 255.0, 0.0, 1.0)
            except Exception as exc:  # noqa: BLE001
                print(f"[remove_background] refine foreground skipped: {exc}")
        thr = _rmbg_mask_threshold() / 255.0
        if thr > 0:
            alpha = np.where(alpha > thr, alpha, 0.0)
        out = _apply_alpha_rgba(rgb, alpha)
        metrics = _mask_metrics_alpha(alpha)
        ratio = metrics["ratio"]
        fg = alpha > 0.05
        conf = float(np.mean(alpha[fg])) if fg.any() else 0.0
        conf = min(0.99, max(0.35, conf))
        print(
            f"[remove_background] RMBG-2.0 ok ratio={ratio:.3f} conf={conf:.3f} "
            f"coverage={metrics.get('coverage_ok')}"
        )
        return out, ratio, conf, metrics
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] RMBG-2.0 failed: {exc}")
        return None


def _rembg_remove(img: Image.Image) -> tuple[Image.Image, float, float, dict] | None:
    try:
        from rembg import remove
    except Exception:
        return None
    try:
        kwargs: dict = {}
        if os.getenv("REMBG_ALPHA_MATTING", "1").lower() in ("1", "true", "yes"):
            kwargs.update(
                {
                    "alpha_matting": True,
                    "alpha_matting_foreground_threshold": 240,
                    "alpha_matting_background_threshold": 20,
                    "alpha_matting_erode_size": 10,
                }
            )
        out = remove(img.convert("RGB"), **kwargs)
        if not isinstance(out, Image.Image):
            out = Image.open(__import__("io").BytesIO(out)).convert("RGBA")
        else:
            out = out.convert("RGBA")
        metrics = _mask_metrics(_alpha_from_rgba(out))
        ratio = metrics["ratio"]
        conf = min(0.99, 0.55 + ratio * 0.4)
        return out, ratio, conf, metrics
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] rembg failed: {exc}")
        return None


def _deeplab_remove(img: Image.Image) -> tuple[Image.Image, float, float, dict] | None:
    global _deeplab_model
    try:
        import torch
        from torchvision import transforms
        from torchvision.models.segmentation import DeepLabV3_ResNet50_Weights, deeplabv3_resnet50
    except Exception:
        return None
    try:
        if _deeplab_model is None:
            weights = DeepLabV3_ResNet50_Weights.DEFAULT
            _deeplab_model = deeplabv3_resnet50(weights=weights)
            _deeplab_model.eval()
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _deeplab_model.to(device)
        preprocess = transforms.Compose(
            [
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )
        rgb = img.convert("RGB")
        tensor = preprocess(rgb).unsqueeze(0).to(device)
        with torch.no_grad():
            out = _deeplab_model(tensor)["out"][0]
            probs = torch.softmax(out, dim=0)
            conf_map, pred = probs.max(0)
            fg = (pred != 0).cpu().numpy().astype(np.uint8)
            mean_conf = float(conf_map.cpu().numpy()[fg.astype(bool)].mean()) if fg.any() else 0.0
        ratio = _mask_ratio(fg)
        if mean_conf < 0.5:
            return None
        out = _apply_mask_rgba(rgb, fg)
        metrics = _mask_metrics(fg)
        return out, ratio, mean_conf, metrics
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] DeepLab failed: {exc}")
        return None


def _get_sam():
    global _sam_predictor
    if _sam_predictor is not None:
        return _sam_predictor
    ckpt = os.getenv("SAM_CHECKPOINT", "/app/weights/sam/sam_vit_b.pth")
    model_type = os.getenv("SAM_MODEL_TYPE", "vit_b")
    if not Path(ckpt).exists():
        return None
    try:
        import torch
        from segment_anything import SamPredictor, sam_model_registry
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] SAM import failed: {exc}")
        return None
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        sam = sam_model_registry[model_type](checkpoint=ckpt)
        sam.to(device=device)
        _sam_predictor = SamPredictor(sam)
        return _sam_predictor
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] SAM load failed: {exc}")
        return None


def _sam_remove(img: Image.Image, seed_mask: np.ndarray | None = None) -> tuple[Image.Image, float, float, dict] | None:
    predictor = _get_sam()
    if predictor is None:
        return None
    try:
        rgb = np.array(img.convert("RGB"))
        h, w = rgb.shape[:2]
        predictor.set_image(rgb)
        if seed_mask is not None and seed_mask.any():
            ys, xs = np.where(seed_mask > 0)
            cx, cy = int(xs.mean()), int(ys.mean())
            point_coords = np.array([[cx, cy]])
            point_labels = np.array([1])
            masks, scores, _ = predictor.predict(
                point_coords=point_coords,
                point_labels=point_labels,
                multimask_output=True,
            )
        else:
            box = np.array([w * 0.1, h * 0.1, w * 0.9, h * 0.9])
            masks, scores, _ = predictor.predict(
                point_coords=np.array([[w // 2, h // 2]]),
                point_labels=np.array([1]),
                box=box[None, :],
                multimask_output=True,
            )
        best = int(np.argmax(scores))
        fg = masks[best].astype(np.uint8)
        conf = float(scores[best])
        ratio = _mask_ratio(fg)
        out = _apply_mask_rgba(img, fg)
        metrics = _mask_metrics(fg)
        return out, ratio, conf, metrics
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] SAM failed: {exc}")
        return None


def _grabcut_remove(img: Image.Image) -> tuple[Image.Image, float, float, dict] | None:
    try:
        import cv2
    except Exception:
        return None
    try:
        rgb = np.array(img.convert("RGB"))
        h, w = rgb.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        margin = max(2, min(h, w) // 30)
        rect = (margin, margin, w - 2 * margin, h - 2 * margin)
        cv2.grabCut(rgb, mask, rect, bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
        fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
        ratio = _mask_ratio(fg)
        out = _apply_mask_rgba(img, fg)
        metrics = _mask_metrics(fg)
        return out, ratio, 0.6, metrics
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] GrabCut failed: {exc}")
        return None


def _frame_usable(name: str, ratio: float, *, min_ratio: float, max_ratio: float) -> bool:
    if name == "copy_rgba":
        return False
    return min_ratio <= ratio <= max_ratio


def _view00_index(files: list[Path]) -> int:
    for i, f in enumerate(files):
        if f.name.lower().startswith("view_00"):
            return i
    return 0


def _segmentation_hard_fail(
    stats: list[dict],
    files: list[Path],
    *,
    min_ratio: float,
    max_ratio: float,
    hard_min_conf: float,
) -> str | None:
    if not stats:
        return "no_frames"
    view_i = _view00_index(files)
    v0 = stats[view_i]
    if not _frame_usable(v0["method"], v0["ratio"], min_ratio=min_ratio, max_ratio=max_ratio):
        return f"view_00_unusable method={v0['method']} ratio={v0['ratio']:.3f}"
    if not v0.get("coverage_ok", True):
        return (
            f"view_00_incomplete height={v0.get('height_frac')} "
            f"width={v0.get('width_frac')}"
        )
    usable = sum(
        1
        for s in stats
        if _frame_usable(s["method"], s["ratio"], min_ratio=min_ratio, max_ratio=max_ratio)
    )
    if usable == 0:
        return "no_usable_masks"
    avg_conf = float(np.mean([s["confidence"] for s in stats]))
    if avg_conf < hard_min_conf:
        return f"avg_conf={avg_conf:.3f} < hard_min={hard_min_conf}"
    return None


def _method_rank(
    name: str,
    ratio: float,
    conf: float,
    metrics: dict,
    *,
    min_ratio: float,
    max_ratio: float,
) -> tuple:
    coverage = bool(metrics.get("coverage_ok"))
    in_ratio = min_ratio <= ratio <= max_ratio
    height = float(metrics.get("height_frac") or 0.0)
    width = float(metrics.get("width_frac") or 0.0)
    method_bonus = {"rmbg2": 0.05, "sam": 0.02, "grabcut": 0.01, "deeplab": 0.005}.get(name, 0.0)
    return (
        1 if coverage else 0,
        1 if in_ratio else 0,
        height + width,
        ratio,
        conf + method_bonus,
    )


def _legacy_methods(img: Image.Image) -> list[tuple[str, Image.Image, float, float, dict]]:
    methods: list[tuple[str, Image.Image, float, float, dict]] = []
    dl = _deeplab_remove(img)
    if dl:
        methods.append(("deeplab", dl[0], dl[1], dl[2], dl[3]))
    rem = _rembg_remove(img)
    if rem:
        methods.append(("rembg", rem[0], rem[1], rem[2], rem[3]))
    seed = None
    if dl:
        seed = (np.array(dl[0])[:, :, 3] > 10).astype(np.uint8)
    elif rem:
        seed = (np.array(rem[0])[:, :, 3] > 10).astype(np.uint8)
    best_coverage = any(m[4].get("coverage_ok") for m in methods)
    if not best_coverage or os.getenv("NOBG_ALWAYS_SAM", "0").lower() in ("1", "true", "yes"):
        sam = _sam_remove(img, seed)
        if sam:
            methods.append(("sam", sam[0], sam[1], sam[2], sam[3]))
    gc = _grabcut_remove(img)
    if gc:
        methods.append(("grabcut", gc[0], gc[1], gc[2], gc[3]))
    return methods


def process_one(
    src: Path,
    dst: Path,
    *,
    conf_thr: float = 0.85,
    min_ratio: float = 0.05,
    max_ratio: float = 0.95,
) -> dict:
    img = Image.open(src)
    engine = _nobg_engine()
    fallback = os.getenv("NOBG_FALLBACK_LEGACY", "0").strip().lower() in ("1", "true", "yes")
    methods: list[tuple[str, Image.Image, float, float, dict]] = []

    if engine == "rmbg2":
        for attempt in range(2):
            rmbg = _rmbg2_remove(img)
            if rmbg:
                methods.append(("rmbg2", rmbg[0], rmbg[1], rmbg[2], rmbg[3]))
                break
            if attempt == 0:
                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:  # noqa: BLE001
                    pass
        if not methods and fallback:
            print("[remove_background] RMBG-2.0 failed → legacy fallback")
            methods.extend(_legacy_methods(img))
        elif not methods:
            print("[remove_background] RMBG-2.0 failed, NOBG_FALLBACK_LEGACY=0")
    elif engine != "legacy":
        rmbg = _rmbg2_remove(img)
        if rmbg:
            methods.append(("rmbg2", rmbg[0], rmbg[1], rmbg[2], rmbg[3]))
        if not methods or fallback:
            methods.extend(_legacy_methods(img))
    else:
        methods.extend(_legacy_methods(img))

    if not methods:
        img.convert("RGBA").save(dst)
        return {
            "method": "copy_rgba",
            "ratio": 1.0,
            "confidence": 0.0,
            "ok": False,
            "quality_ok": False,
            "coverage_ok": False,
        }

    methods.sort(
        key=lambda m: _method_rank(
            m[0], m[2], m[3], m[4], min_ratio=min_ratio, max_ratio=max_ratio
        ),
        reverse=True,
    )
    name, out_im, ratio, conf, metrics = methods[0]
    out_im.save(dst)
    usable = _frame_usable(name, ratio, min_ratio=min_ratio, max_ratio=max_ratio)
    coverage_ok = bool(metrics.get("coverage_ok"))
    return {
        "method": name,
        "ratio": ratio,
        "confidence": conf,
        "ok": usable and coverage_ok,
        "quality_ok": conf >= conf_thr,
        "coverage_ok": coverage_ok,
        "height_frac": metrics.get("height_frac"),
        "width_frac": metrics.get("width_frac"),
    }


_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _photo_files(photos: Path) -> list[Path]:
    all_images = sorted(
        p for p in photos.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
    )
    views = [p for p in all_images if p.name.lower().startswith("view_")]
    return views if views else all_images


def _view_index(path: Path) -> int:
    name = path.stem.lower()
    if name.startswith("view_"):
        try:
            return int(name.split("_", 1)[1])
        except ValueError:
            return 10_000
    return 10_000


def _file_fingerprint(path: Path) -> bytes:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.digest()


def _unique_by_content(files: list[Path]) -> list[Path]:
    seen: dict[bytes, Path] = {}
    for path in sorted(files, key=_view_index):
        fp = _file_fingerprint(path)
        if fp not in seen:
            seen[fp] = path
    return list(seen.values())


def _select_files(files: list[Path], task_dir: Path | None = None) -> list[Path]:
    """
    Для multi-photo (3/5/6/12) обрабатываем все исходные ракурсы, не только view_00.

    NOBG_VIEW00_ONLY=1 остаётся ускорением для режима 1 фото; при photo_count>1
    игнорируется, иначе боковые снимки не доходят до TRELLIS.
    """
    if not files:
        return files

    photo_count = _photo_count_hint(task_dir)
    unique = _unique_by_content(files)

    # Явно одно фото / единственный уникальный кадр → только front.
    # При 2+ уникальных НЕ режем до view_00 даже если NOBG_VIEW00_ONLY=1 и photo_count потерян.
    if photo_count == 1 or (len(unique) <= 1 and _view00_only()):
        for f in files:
            if f.name.lower().startswith("view_00"):
                print(f"[remove_background] single-image: только {f.name} (NOBG_VIEW00_ONLY)")
                return [f]
        return files[:1]

    seed_indices = _VIEW_INDICES_BY_COUNT.get(photo_count or 0)
    selected: list[Path] = []
    if seed_indices:
        by_idx = {_view_index(p): p for p in files}
        for idx in seed_indices:
            path = by_idx.get(idx)
            if path is not None:
                selected.append(path)
        selected = _unique_by_content(selected)

    if len(selected) < min(2, len(unique)):
        selected = unique

    # Multi-photo: не даём TRELLIS2_MAX_VIEWS=1 выкинуть боковые кадры.
    max_raw = (os.getenv("TRELLIS2_MAX_VIEWS") or "6").strip()
    try:
        max_cap = max(1, int(max_raw))
    except ValueError:
        max_cap = 6
    min_required = len(selected) if (photo_count and photo_count > 1) or len(selected) > 1 else 1
    effective_cap = max(max_cap, min_required) if min_required > 1 else max_cap
    if len(selected) > effective_cap:
        selected = selected[:effective_cap]

    names = ", ".join(p.name for p in selected)
    print(
        f"[remove_background] multi-view: {len(selected)} кадров "
        f"(photo_count={photo_count}, unique={len(unique)}, cap={effective_cap}): {names}"
    )
    return selected


def _stub_copy_nobg(files: list[Path], out: Path) -> list[dict]:
    stats: list[dict] = []
    for f in files:
        dst = out / (f.stem + ".png")
        Image.open(f).convert("RGBA").save(dst)
        stats.append(
            {"method": "stub_copy", "ratio": 1.0, "confidence": 1.0, "ok": True, "quality_ok": True}
        )
    return stats


def main(task_dir: str) -> None:
    root = Path(task_dir)
    photos = root / "photos"
    out = root / "photos_nobg"
    out.mkdir(parents=True, exist_ok=True)
    photos.mkdir(parents=True, exist_ok=True)

    files = _select_files(_photo_files(photos), task_dir=root)
    if not files:
        print(f"[remove_background] нет фото в {photos}")
        raise SystemExit(2)

    skip_nobg = os.getenv("WORKER_REAL_NOBG", "1") not in ("1", "true", "yes")
    if skip_nobg or os.getenv("WORKER_PIPELINE_MODE", "").lower() == "stub":
        stats = _stub_copy_nobg(files, out)
        print(f"[remove_background] stub copy {len(files)} frames (skip ML)")
        meta_path = root / "task_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        meta["segmentation"] = {
            "frames": stats,
            "avg_confidence": 1.0,
            "threshold": 0.0,
            "weak_frames": 0,
            "stub": True,
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        return

    quality_target = float(os.getenv("NOBG_CONFIDENCE", "0.80"))
    hard_min = float(os.getenv("NOBG_HARD_FAIL_MIN", "0.35"))
    min_r = float(os.getenv("NOBG_MIN_RATIO", "0.05"))
    max_r = float(os.getenv("NOBG_MAX_RATIO", "0.95"))
    stats = []
    weak = 0
    low_quality = 0
    for f in files:
        dst = out / (f.stem + ".png")
        info = process_one(f, dst, conf_thr=quality_target, min_ratio=min_r, max_ratio=max_r)
        print(f"[remove_background] {f.name} → {info}")
        stats.append(info)
        if not info["ok"]:
            weak += 1
        if not info.get("quality_ok", info["ok"]):
            low_quality += 1

    meta_path = root / "task_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    avg_conf = float(np.mean([s["confidence"] for s in stats])) if stats else 0.0
    quality_warning = avg_conf < quality_target or low_quality > 0
    fail_reason = _segmentation_hard_fail(
        stats,
        files,
        min_ratio=min_r,
        max_ratio=max_r,
        hard_min_conf=hard_min,
    )
    meta["segmentation"] = {
        "engine": _nobg_engine(),
        "model": os.getenv("NOBG_MODEL_ID", "briaai/RMBG-2.0"),
        "frames": stats,
        "avg_confidence": avg_conf,
        "threshold": quality_target,
        "hard_fail_min": hard_min,
        "weak_frames": weak,
        "low_quality_frames": low_quality,
        "quality_warning": quality_warning,
        "view00_only": _view00_only(),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    if fail_reason:
        strict = os.getenv("NOBG_STRICT_SEGMENTATION", "0").strip().lower() in ("1", "true", "yes")
        soft_ok = avg_conf >= hard_min and any(
            (out / (f.stem + ".png")).exists() for f in files
        )
        if not strict and soft_ok:
            print(
                f"[remove_background] warning {fail_reason} — "
                "продолжаем (NOBG_STRICT_SEGMENTATION=0)"
            )
            meta["segmentation"]["quality_warning"] = True
            meta["segmentation"]["segmentation_warning"] = fail_reason
            meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        else:
            print(f"[remove_background] failed_segmentation {fail_reason}")
            raise SystemExit(3)
    print(
        f"[remove_background] done {len(files)} avg_conf={avg_conf:.3f} "
        f"weak={weak} low_quality={low_quality} warn={quality_warning}"
    )
    _release_rmbg2()


if __name__ == "__main__":
    main(sys.argv[1])
