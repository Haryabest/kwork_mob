"""Приёмка DWT: устойчивость к JPEG/WebP quality 80% (§1.3 / §5.4.4 / §10.5).

Запуск:
  cd worker && python -m pytest tests/test_dwt_jpeg_webp.py -q
"""

from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from apply_watermark import _bits_from_meta, embed_dwt_dct, extract_bits_dwt  # noqa: E402


def _bit_match_ratio(a: list[int], b: list[int]) -> float:
    n = min(len(a), len(b))
    assert n > 0
    return sum(1 for i in range(n) if a[i] == b[i]) / n


def _rich_texture(size: int = 512) -> Image.Image:
    """Нетекстура-шум с низкочастотной структурой — ближе к diffuse товара."""
    rng = np.random.default_rng(42)
    base = rng.integers(40, 220, size=(size, size, 3), dtype=np.uint8).astype(np.float64)
    yy, xx = np.mgrid[0:size, 0:size]
    wave = 40 * np.sin(xx / 18.0) + 30 * np.cos(yy / 22.0)
    out = np.clip(base + wave[:, :, None], 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


@pytest.fixture
def marked_pair():
    ts = int(time.time())
    bits = _bits_from_meta(user_id=7, company_id=3, order_id=42, ts=ts, n_bits=128)
    src = _rich_texture(512)
    marked = embed_dwt_dct(src, bits, strength=0.02)
    return marked, bits


def test_dwt_roundtrip_png(marked_pair):
    marked, bits = marked_pair
    got = extract_bits_dwt(marked, n_bits=128)
    assert _bit_match_ratio(got, bits) >= 0.95


def test_dwt_survives_jpeg_q80(marked_pair):
    marked, bits = marked_pair
    buf = io.BytesIO()
    marked.save(buf, format="JPEG", quality=80)
    buf.seek(0)
    compressed = Image.open(buf).convert("RGB")
    got = extract_bits_dwt(compressed, n_bits=128)
    ratio = _bit_match_ratio(got, bits)
    assert ratio >= 0.80, f"JPEG q80 bit match {ratio:.3f} < 0.80"


def test_dwt_survives_webp_q80(marked_pair):
    marked, bits = marked_pair
    buf = io.BytesIO()
    marked.save(buf, format="WEBP", quality=80)
    buf.seek(0)
    compressed = Image.open(buf).convert("RGB")
    got = extract_bits_dwt(compressed, n_bits=128)
    ratio = _bit_match_ratio(got, bits)
    assert ratio >= 0.80, f"WebP q80 bit match {ratio:.3f} < 0.80"


def test_dwt_survives_resize_80pct(marked_pair):
    marked, bits = marked_pair
    w, h = marked.size
    small = marked.resize((int(w * 0.8), int(h * 0.8)), Image.Resampling.BICUBIC)
    restored = small.resize((w, h), Image.Resampling.BICUBIC)
    got = extract_bits_dwt(restored, n_bits=128)
    ratio = _bit_match_ratio(got, bits)
    assert ratio >= 0.75, f"resize 80% bit match {ratio:.3f} < 0.75"
