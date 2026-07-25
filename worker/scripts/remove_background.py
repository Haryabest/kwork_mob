"""Двухступенчатое удаление фона §6.1.1: rembg → DeepLabV3+ → SAM → GrabCut."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_sam_predictor = None


def _mask_ratio(mask: np.ndarray) -> float:
    m = mask.astype(bool)
    if m.size == 0:
        return 0.0
    return float(m.mean())


def _apply_mask_rgba(img: Image.Image, mask: np.ndarray) -> Image.Image:
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    m = (mask > 0).astype(np.uint8) * 255
    arr[:, :, 3] = m
    return Image.fromarray(arr, "RGBA")


def _rembg_remove(img: Image.Image) -> tuple[Image.Image, float, float] | None:
    try:
        from rembg import remove
    except Exception:
        return None
    try:
        out = remove(img.convert("RGB"))
        if not isinstance(out, Image.Image):
            out = Image.open(__import__("io").BytesIO(out)).convert("RGBA")
        else:
            out = out.convert("RGBA")
        alpha = np.array(out)[:, :, 3]
        ratio = _mask_ratio(alpha > 10)
        conf = min(0.99, 0.55 + ratio * 0.4)
        return out, ratio, conf
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] rembg failed: {exc}")
        return None


_deeplab_model = None


def _deeplab_remove(img: Image.Image) -> tuple[Image.Image, float, float] | None:
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
        return _apply_mask_rgba(rgb, fg), ratio, mean_conf
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


def _sam_remove(img: Image.Image, seed_mask: np.ndarray | None = None) -> tuple[Image.Image, float, float] | None:
    predictor = _get_sam()
    if predictor is None:
        return None
    try:
        import torch

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
            # центральная точка + box по кадру
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
        return _apply_mask_rgba(img, fg), ratio, conf
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] SAM failed: {exc}")
        return None


def _grabcut_remove(img: Image.Image) -> tuple[Image.Image, float, float] | None:
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
        margin = max(2, min(h, w) // 20)
        rect = (margin, margin, w - 2 * margin, h - 2 * margin)
        cv2.grabCut(rgb, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
        fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
        ratio = _mask_ratio(fg)
        return _apply_mask_rgba(img, fg), ratio, 0.6
    except Exception as exc:  # noqa: BLE001
        print(f"[remove_background] GrabCut failed: {exc}")
        return None


def _frame_usable(name: str, ratio: float, *, min_ratio: float, max_ratio: float) -> bool:
    """Маска пригодна для пайплайна: не fallback и доля объекта в кадре в норме."""
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
    """Жёсткий провал только при реально битой сегментации (не из-за порога quality)."""
    if not stats:
        return "no_frames"
    view_i = _view00_index(files)
    v0 = stats[view_i]
    if not _frame_usable(v0["method"], v0["ratio"], min_ratio=min_ratio, max_ratio=max_ratio):
        return f"view_00_unusable method={v0['method']} ratio={v0['ratio']:.3f}"
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


def process_one(
    src: Path,
    dst: Path,
    *,
    conf_thr: float = 0.85,
    min_ratio: float = 0.10,
    max_ratio: float = 0.95,
) -> dict:
    img = Image.open(src)
    methods: list[tuple[str, tuple]] = []

    # §6.1.1: DeepLab primary, rembg fallback
    dl = _deeplab_remove(img)
    if dl:
        methods.append(("deeplab", dl))
    rem = _rembg_remove(img)
    if rem:
        methods.append(("rembg", rem))

    # SAM: если DeepLab/rembg слабые по confidence — обязательный fallback §6.1.1
    need_sam = True
    if dl and dl[2] >= conf_thr and min_ratio <= dl[1] <= max_ratio:
        need_sam = False
    if rem and rem[2] >= conf_thr and min_ratio <= rem[1] <= max_ratio:
        need_sam = False
    if need_sam:
        seed = None
        if dl:
            seed = (np.array(dl[0])[:, :, 3] > 10).astype(np.uint8)
        elif rem:
            seed = (np.array(rem[0])[:, :, 3] > 10).astype(np.uint8)
        sam = _sam_remove(img, seed)
        if sam:
            methods.append(("sam", sam))

    gc = _grabcut_remove(img)
    if gc:
        methods.append(("grabcut", gc))

    # выбираем лучший по confidence среди валидных ratio
    valid = [(n, r, c, im) for n, (im, r, c) in methods if min_ratio <= r <= max_ratio]
    if not valid:
        valid = [(n, r, c, im) for n, (im, r, c) in methods]

    if valid:
        valid.sort(key=lambda x: x[2], reverse=True)
        name, ratio, conf, out_im = valid[0]
        out_im.save(dst)
        usable = _frame_usable(name, ratio, min_ratio=min_ratio, max_ratio=max_ratio)
        return {
            "method": name,
            "ratio": ratio,
            "confidence": conf,
            "ok": usable,
            "quality_ok": conf >= conf_thr,
        }

    img.convert("RGBA").save(dst)
    return {
        "method": "copy_rgba",
        "ratio": 1.0,
        "confidence": 0.0,
        "ok": False,
        "quality_ok": False,
    }


_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _photo_files(photos: Path) -> list[Path]:
    """Только ракурсы view_XX.*; игнорируем metadata.json, source.zip и пр."""
    all_images = sorted(
        p for p in photos.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
    )
    views = [p for p in all_images if p.name.lower().startswith("view_")]
    return views if views else all_images


def _stub_copy_nobg(files: list[Path], out: Path) -> list[dict]:
    """Stub / WORKER_REAL_NOBG=0: копируем JPEG → PNG без ML."""
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

    files = _photo_files(photos)
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

  # Порог качества для score/alerts; не блокирует пайплайн (rembg conf ≈ 0.55+ratio*0.4).
    quality_target = float(os.getenv("NOBG_CONFIDENCE", "0.85"))
    hard_min = float(os.getenv("NOBG_HARD_FAIL_MIN", "0.35"))
    min_r = float(os.getenv("NOBG_MIN_RATIO", "0.10"))
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
        "frames": stats,
        "avg_confidence": avg_conf,
        "threshold": quality_target,
        "hard_fail_min": hard_min,
        "weak_frames": weak,
        "low_quality_frames": low_quality,
        "quality_warning": quality_warning,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    if fail_reason:
        print(f"[remove_background] failed_segmentation {fail_reason}")
        raise SystemExit(3)
    print(
        f"[remove_background] done {len(files)} avg_conf={avg_conf:.3f} "
        f"weak={weak} low_quality={low_quality} warn={quality_warning}"
    )


if __name__ == "__main__":
    main(sys.argv[1])
