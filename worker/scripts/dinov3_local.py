"""Локальные веса DINOv3 — обход gated HF (facebook/dinov3-vitl16-pretrain-lvd1689m)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

DEFAULT_LOCAL = Path("/var/lib/worker/dinov3-vitl16")
HUB_ID = "facebook/dinov3-vitl16-pretrain-lvd1689m"
CACHE_NAME = "models--" + HUB_ID.replace("/", "--")


def _weight_file_ok(path: Path) -> bool:
    try:
        return path.is_file() and path.resolve().stat().st_size > 1_000_000
    except OSError:
        return False


def _has_weights(path: Path) -> bool:
    if not (path / "config.json").is_file():
        return False
    if _weight_file_ok(path / "model.safetensors"):
        return True
    return any(_weight_file_ok(p) for p in path.glob("*.safetensors"))


def _cache_roots() -> list[Path]:
    roots: list[Path] = []
    for raw in (
        os.getenv("HF_HOME", ""),
        os.getenv("HUGGINGFACE_HUB_CACHE", ""),
        "/root/.cache/huggingface",
        str(Path.home() / ".cache" / "huggingface"),
    ):
        if raw:
            roots.append(Path(raw).expanduser())
    seen: set[str] = set()
    out: list[Path] = []
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            out.append(root)
    return out


def _find_hf_snapshot() -> Path | None:
    for root in _cache_roots():
        hub = root / "hub" / CACHE_NAME / "snapshots"
        if not hub.is_dir():
            continue
        snaps = sorted(hub.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for snap in snaps:
            if _has_weights(snap):
                return snap
    return None


def resolve_dinov3_local() -> Path | None:
    candidates: list[Path] = []
    env = (os.getenv("TRELLIS2_DINOV3_LOCAL") or "").strip()
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(DEFAULT_LOCAL)
    for path in candidates:
        if _has_weights(path):
            return path
    snap = _find_hf_snapshot()
    return snap


@contextmanager
def _dinov3_local_files_only():
    from transformers import DINOv3ViTModel

    orig = DINOv3ViTModel.from_pretrained

    @classmethod
    def _wrapped(cls, *args, **kwargs):
        kwargs["local_files_only"] = True
        return orig.__func__(cls, *args, **kwargs)

    DINOv3ViTModel.from_pretrained = _wrapped  # type: ignore[method-assign]
    try:
        yield
    finally:
        DINOv3ViTModel.from_pretrained = orig


def apply_local_dinov3_patch() -> bool:
    local = resolve_dinov3_local()
    if local is None:
        print("[dinov3-local] веса не найдены", flush=True)
        return False

    from trellis2.modules import image_feature_extractor as fe  # type: ignore

    if getattr(fe.DinoV3FeatureExtractor, "_kwork_local_dinov3", False):
        return True

    local_s = str(local)
    orig_init = fe.DinoV3FeatureExtractor.__init__

    def patched_init(self, model_name: str, image_size: int = 512) -> None:
        use = local_s if "dinov3" in str(model_name).lower() else model_name
        print(f"[dinov3-local] {model_name} → {use}", flush=True)
        if use == local_s:
            with _dinov3_local_files_only():
                orig_init(self, use, image_size=image_size)
        else:
            orig_init(self, model_name, image_size=image_size)

    fe.DinoV3FeatureExtractor.__init__ = patched_init  # type: ignore[method-assign]
    fe.DinoV3FeatureExtractor._kwork_local_dinov3 = True  # type: ignore[attr-defined]
    print(f"[dinov3-local] готово: {local_s}", flush=True)
    return True
