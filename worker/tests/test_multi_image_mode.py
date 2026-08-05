"""Defaults multi-view mode (без GPU)."""

from __future__ import annotations

import pytest

from trellis_runtime import multi_image_mode


def test_geometry_default_multidiffusion(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TRELLIS2_MULTI_IMAGE_MODE", raising=False)
    assert multi_image_mode("geometry") == "multidiffusion"


def test_texture_default_multidiffusion(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TRELLIS2_MULTI_IMAGE_MODE_TEX", raising=False)
    assert multi_image_mode("texture") == "multidiffusion"


def test_geometry_stochastic_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TRELLIS2_MULTI_IMAGE_MODE", "stochastic")
    assert multi_image_mode("geometry") == "stochastic"
