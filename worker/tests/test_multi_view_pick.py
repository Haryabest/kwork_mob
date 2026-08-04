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


def test_pick_three_seed_views_keeps_all_sides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """3 фото: фронт + лево + право — все три должны попасть в TRELLIS."""
    photos = tmp_path / "photos_nobg"
    _write(photos / "view_00.png", b"front-unique-bytes-aaa")
    _write(photos / "view_03.png", b"left-unique-bytes-bbb")
    _write(photos / "view_09.png", b"right-unique-bytes-ccc")
    _write(photos / "view_01.png", b"front-unique-bytes-aaa")

    monkeypatch.setenv("PHOTO_COUNT", "3")
    monkeypatch.setenv("TRELLIS2_MAX_VIEWS", "6")

    picked = pick_input_images(photos, task_dir=tmp_path)
    names = [p.name for p in picked]
    assert names == ["view_00.png", "view_03.png", "view_09.png"]


def test_pick_ignores_max_views_one_for_multi_photo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Регрессия дыр на боках: MAX_VIEWS=1 в старом .env не должен резать 3-фото до view_00."""
    photos = tmp_path / "photos_nobg"
    _write(photos / "view_00.png", b"a")
    _write(photos / "view_03.png", b"b")
    _write(photos / "view_09.png", b"c")

    monkeypatch.setenv("PHOTO_COUNT", "3")
    monkeypatch.setenv("TRELLIS2_MAX_VIEWS", "1")

    picked = pick_input_images(photos, task_dir=tmp_path)
    names = [p.name for p in picked]
    assert names == ["view_00.png", "view_03.png", "view_09.png"]


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
