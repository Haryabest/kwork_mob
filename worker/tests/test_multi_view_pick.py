"""Unit tests: multi-view input selection (без GPU)."""

from __future__ import annotations

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
