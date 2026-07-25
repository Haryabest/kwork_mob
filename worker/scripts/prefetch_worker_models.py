"""Однократная загрузка весов HF в кэш (/root/.cache/huggingface)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _token() -> str | None:
    t = (os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN") or "").strip()
    return t or None


def _snap(repo: str) -> None:
    from huggingface_hub import snapshot_download

    print(f"[prefetch] snapshot {repo} …", flush=True)
    path = snapshot_download(
        repo_id=repo,
        token=_token(),
        resume_download=True,
    )
    print(f"[prefetch] OK {repo} → {path}", flush=True)


def _warm_rmbg() -> None:
    nobg = (os.getenv("NOBG_ENGINE") or "rmbg2").strip().lower()
    if nobg == "legacy":
        return
    repo = (os.getenv("NOBG_MODEL_ID") or "briaai/RMBG-2.0").strip()
    _snap(repo)


def _warm_trellis() -> None:
    ver = (os.getenv("TRELLIS_VERSION") or "2").strip().lower()
    if ver not in ("2", "trellis2", "trellis.2"):
        return
    repo = (os.getenv("TRELLIS_WEIGHTS") or "microsoft/TRELLIS.2-4B").strip()
    _snap(repo)


def main() -> int:
    cache = os.getenv("HF_HOME") or os.getenv("HUGGINGFACE_HUB_CACHE") or "/root/.cache/huggingface"
    print(f"[prefetch] HF cache: {cache}", flush=True)
    Path(cache).mkdir(parents=True, exist_ok=True)
    _warm_rmbg()
    _warm_trellis()
    print("[prefetch] все модели в локальном кэше", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[prefetch] FAILED: {exc}", flush=True)
        raise
