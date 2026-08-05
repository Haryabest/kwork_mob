"""Synthetic back view for 3-photo geometry."""

from __future__ import annotations

from PIL import Image

import pytest

from trellis_runtime import geometry_view_images


def test_geometry_adds_mirrored_front_for_3_photo(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TRELLIS2_SYNTHETIC_BACK_VIEW", "1")
    front = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
    left = Image.new("RGBA", (64, 64), (0, 255, 0, 255))
    right = Image.new("RGBA", (64, 64), (0, 0, 255, 255))
    out, added = geometry_view_images([front, left, right], task_dir=None)
    assert added is True
    assert len(out) == 4
    assert out[3].size == front.size
    # зеркало: левый пиксель фронта → правый на «тыле»
    assert out[3].getpixel((63, 32)) == front.getpixel((0, 32))


def test_geometry_skips_when_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TRELLIS2_SYNTHETIC_BACK_VIEW", "0")
    imgs = [Image.new("RGBA", (8, 8)) for _ in range(3)]
    out, added = geometry_view_images(imgs, task_dir=None)
    assert added is False
    assert len(out) == 3


def test_geometry_skips_single_photo(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TRELLIS2_SYNTHETIC_BACK_VIEW", "1")
    imgs = [Image.new("RGBA", (8, 8))]
    out, added = geometry_view_images(imgs, task_dir=None)
    assert added is False
    assert len(out) == 1
