"""Unit tests: multi-view input selection (без GPU)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from trellis_runtime import pick_input_images


def _write(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_pick_three_seed_views_keeps_sides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Регрессия: при 3 фото брать фронт + левый (90°) + правый (270°)."""
    photos = tmp_path / "photos_nobg"
    _write(photos / "view_00.png", b"front-unique-bytes-aaa")
    _write(photos / "view_03.png", b"left-unique-bytes-bbb")
    _write(photos / "view_09.png", b"right-unique-bytes-ccc")
    # expand-копии не должны подменять выбор
    _write(photos / "view_01.png", b"front-unique-bytes-aaa")
    _write(photos / "view_06.png", b"left-unique-bytes-bbb")

    monkeypatch.setenv("PHOTO_COUNT", "3")
    monkeypatch.setenv("TRELLIS2_MAX_VIEWS", "6")
    monkeypatch.setenv("TRELLIS2_MULTI_IMAGE_MODE", "multidiffusion")

    picked = pick_input_images(photos, task_dir=tmp_path)
    names = [p.name for p in picked]
    assert names == ["view_00.png", "view_03.png", "view_09.png"]


def test_pick_legacy_048_fallback_to_unique(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Старые заказы со слотами [0,4,8]: если новых [0,3,9] нет — берём уникальный контент."""
    photos = tmp_path / "photos_nobg"
    _write(photos / "view_00.png", b"front-unique-bytes-aaa")
    _write(photos / "view_04.png", b"side-unique-bytes-bbb")
    _write(photos / "view_08.png", b"rear-unique-bytes-ccc")

    monkeypatch.setenv("PHOTO_COUNT", "3")
    monkeypatch.setenv("TRELLIS2_MAX_VIEWS", "6")

    picked = pick_input_images(photos, task_dir=tmp_path)
    names = [p.name for p in picked]
    assert names == ["view_00.png", "view_04.png", "view_08.png"]


def test_pick_does_not_linspace_skip_middle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """MAX_VIEWS=2 раньше через linspace давал [0,2] — первая и третья без середины."""
    photos = tmp_path / "photos_nobg"
    _write(photos / "view_00.png", b"a")
    _write(photos / "view_03.png", b"b")
    _write(photos / "view_09.png", b"c")

    monkeypatch.setenv("PHOTO_COUNT", "3")
    monkeypatch.setenv("TRELLIS2_MAX_VIEWS", "2")

    picked = pick_input_images(photos, task_dir=tmp_path)
    names = [p.name for p in picked]
    assert names == ["view_00.png", "view_03.png"]
    assert "view_09.png" not in names


def test_pick_single_photo_unique(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    photos = tmp_path / "photos_nobg"
    payload = b"same-front"
    for i in range(12):
        _write(photos / f"view_{i:02d}.png", payload)

    monkeypatch.setenv("PHOTO_COUNT", "1")
    monkeypatch.setenv("TRELLIS2_MAX_VIEWS", "6")

    picked = pick_input_images(photos, task_dir=tmp_path)
    assert len(picked) == 1
    assert picked[0].name.startswith("view_00")
