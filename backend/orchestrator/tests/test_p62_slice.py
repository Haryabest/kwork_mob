"""§8.4 upsell admin, §9.5 lifecycle, §9.6 source expire labels."""

from __future__ import annotations

import pytest

from app.services import minio_lifecycle as mlc
from app.services import upsells as upsell_svc


def test_expected_lifecycle_rules():
    rules = mlc.expected_rules()
    buckets = {r["bucket_key"] for r in rules}
    assert "photos" in buckets
    assert "models" in buckets


def test_upsell_defaults_codes():
    assert "real_scale" in upsell_svc.VALID
    assert "video_360" in upsell_svc.VALID


@pytest.mark.asyncio
async def test_set_upsell_amount(db):
    row = await upsell_svc.set_amount(db, code="real_scale", amount_rub=550)
    assert row.amount_rub == 550


@pytest.mark.asyncio
async def test_source_expire_warn_days():
    from app.services.source_expire import WARN_DAYS

    assert WARN_DAYS == (7, 3, 1)
