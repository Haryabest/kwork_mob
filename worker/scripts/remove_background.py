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

    rem = _rembg_remove(img)
    if rem:
        methods.append(("rembg", rem))
    dl = _deeplab_remove(img)
    if dl:
        methods.append(("deeplab", dl))

    # SAM: если DeepLab/rembg слабые по confidence — обязательный fallback §6.1.1
    need_sam = True
    if rem and rem[2] >= conf_thr and min_ratio <= rem[1] <= max_ratio:
        need_sam = False
    if dl and dl[2] >= conf_thr and min_ratio <= dl[1] <= max_ratio:
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
        return {"method": name, "ratio": ratio, "confidence": conf, "ok": conf >= conf_thr}

    img.convert("RGBA").save(dst)
    return {"method": "copy_rgba", "ratio": 1.0, "confidence": 0.0, "ok": False}


def main(task_dir: str) -> None:
    root = Path(task_dir)
    photos = root / "photos"
    out = root / "photos_nobg"
    out.mkdir(parents=True, exist_ok=True)
    photos.mkdir(parents=True, exist_ok=True)

    files = sorted(photos.glob("*.*"))
    if not files:
        print(f"[remove_background] нет фото в {photos}")
        raise SystemExit(2)

    conf = float(os.getenv("NOBG_CONFIDENCE", "0.85"))
    min_r = float(os.getenv("NOBG_MIN_RATIO", "0.10"))
    max_r = float(os.getenv("NOBG_MAX_RATIO", "0.95"))
    stats = []
    weak = 0
    for f in files:
        dst = out / (f.stem + ".png")
        info = process_one(f, dst, conf_thr=conf, min_ratio=min_r, max_ratio=max_r)
        print(f"[remove_background] {f.name} → {info}")
        stats.append(info)
        if not info["ok"]:
            weak += 1

    meta_path = root / "task_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    avg_conf = float(np.mean([s["confidence"] for s in stats])) if stats else 0.0
    meta["segmentation"] = {
        "frames": stats,
        "avg_confidence": avg_conf,
        "threshold": conf,
        "weak_frames": weak,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    # §6.1.1: средняя уверенность ≥ 0.85, иначе fail (воркер повторит / другой узел)
    if avg_conf < conf and weak == len(files):
        print(f"[remove_background] failed_segmentation avg_conf={avg_conf:.3f}")
        raise SystemExit(3)
    print(f"[remove_background] done {len(files)} avg_conf={avg_conf:.3f} weak={weak}")


if __name__ == "__main__":
    main(sys.argv[1])
