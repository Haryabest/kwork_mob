"""§11.9 upsell price history + admin edit."""

from __future__ import annotations

import pytest

from app.services import upsells as upsell_svc


@pytest.mark.asyncio
async def test_upsell_price_history_on_change(db):
    await upsell_svc.set_amount(db, code="real_scale", amount_rub=600, changed_by=1)
    await db.commit()
    items = await upsell_svc.price_history(db, code="real_scale")
    assert items
    assert items[0]["new_amount"] == 600


@pytest.mark.asyncio
async def test_upsell_active_toggle_history(db):
    await upsell_svc.set_amount(
        db, code="video_360", amount_rub=990, is_active=False, changed_by=1
    )
    await db.commit()
    items = await upsell_svc.price_history(db, code="video_360")
    assert items[0]["new_active"] is False


def test_upsells_history_route():
    from app.api.v1 import admin_finance as fin

    paths = {getattr(r, "path", "") for r in fin.router.routes}
    assert "/upsells/history" in paths
