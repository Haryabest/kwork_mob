"""Локальные веса DINOv3 — обход gated HF (facebook/dinov3-vitl16-pretrain-lvd1689m)."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_LOCAL = Path("/var/lib/worker/dinov3-vitl16")
HUB_ID = "facebook/dinov3-vitl16-pretrain-lvd1689m"


def _has_weights(path: Path) -> bool:
    if not (path / "config.json").is_file():
        return False
    if (path / "model.safetensors").is_file():
        return True
    return any(path.glob("*.safetensors"))


def resolve_dinov3_local() -> Path | None:
    candidates: list[Path] = []
    env = (os.getenv("TRELLIS2_DINOV3_LOCAL") or "").strip()
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(DEFAULT_LOCAL)
    for path in candidates:
        if _has_weights(path):
            return path.resolve()
    return None


def apply_local_dinov3_patch() -> bool:
    local = resolve_dinov3_local()
    if local is None:
        return False

    from trellis2.modules import image_feature_extractor as fe  # type: ignore

    if getattr(fe.DinoV3FeatureExtractor, "_kwork_local_dinov3", False):
        return True

    local_s = str(local)
    orig_init = fe.DinoV3FeatureExtractor.__init__

    def patched_init(self, model_name: str, image_size: int = 512) -> None:
        use = local_s if "dinov3" in str(model_name) else model_name
        print(f"[dinov3-local] {model_name} → {use}", flush=True)
        orig_init(self, use, image_size=image_size)

    fe.DinoV3FeatureExtractor.__init__ = patched_init  # type: ignore[method-assign]
    fe.DinoV3FeatureExtractor._kwork_local_dinov3 = True  # type: ignore[attr-defined]
    print(f"[dinov3-local] готово: {local_s}", flush=True)
    return True
