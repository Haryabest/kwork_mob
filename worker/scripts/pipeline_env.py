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
