"""Флаги режима пайплайна (TRELLIS.2 / stub)."""

from __future__ import annotations

import os


def pipeline_mode() -> str:
    return os.getenv("WORKER_PIPELINE_MODE", "trellis").strip().lower()


def is_stub_pipeline() -> bool:
    return pipeline_mode() == "stub"


def trellis_version() -> str:
    return os.getenv("TRELLIS_VERSION", "2").strip().lower()


def is_trellis2() -> bool:
    return trellis_version() in ("2", "trellis2", "trellis.2")


def is_production_trellis() -> bool:
    return pipeline_mode() == "trellis" and not is_stub_pipeline()


def allow_stub_fallback() -> bool:
    if os.getenv("ENVIRONMENT", "").strip().lower() == "production":
        return False
    return os.getenv("TRELLIS_ALLOW_STUB_FALLBACK", "0").strip() in ("1", "true", "yes")


def assert_production_pipeline() -> None:
    """§6.6: stub pipeline запрещён в production."""
    if os.getenv("ENVIRONMENT", "").strip().lower() == "production" and is_stub_pipeline():
        raise RuntimeError("WORKER_PIPELINE_MODE=stub запрещён в production")


def subprocess_stream_enabled() -> bool:
    return os.getenv("WORKER_SUBPROCESS_STREAM", "1").strip().lower() in ("1", "true", "yes")
