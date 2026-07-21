"""§6.4 SHA download verify, §6.5 presign TTL 30m, §6.6 prod stub policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.core.config import settings
from app.services.integrity import verify_object_sha256
from fastapi import HTTPException


def test_model_presign_ttl_default():
    assert int(settings.MODEL_PRESIGN_TTL_SECONDS) == 1800


def test_verify_object_sha256_mismatch():
    from unittest.mock import patch

    with patch("app.services.integrity.minio_service") as m:
        m.download_bytes.return_value = b"data"
        try:
            verify_object_sha256("b", "k", "deadbeef" * 8)
            raised = False
        except HTTPException as exc:
            raised = True
            assert exc.status_code == 409
    assert raised


def _load_pipeline_env():
    path = Path(__file__).resolve().parents[3] / "worker" / "scripts" / "pipeline_env.py"
    spec = importlib.util.spec_from_file_location("pipeline_env", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_stub_fallback_disabled_in_production(monkeypatch):
    pe = _load_pipeline_env()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TRELLIS_ALLOW_STUB_FALLBACK", "1")
    assert pe.allow_stub_fallback() is False


def test_assert_production_pipeline_blocks_stub(monkeypatch):
    pe = _load_pipeline_env()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("WORKER_PIPELINE_MODE", "stub")
    try:
        pe.assert_production_pipeline()
        ok = False
    except RuntimeError:
        ok = True
    assert ok
