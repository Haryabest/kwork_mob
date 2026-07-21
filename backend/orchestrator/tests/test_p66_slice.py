"""§11.3 CSV import, §11.6 support AI, §11.7 segmentation UI."""

from __future__ import annotations

import pytest

from app.services import admin_csv_import as imp


def test_parse_company_rows():
    csv_text = "name,inn,kpp,ogrn,owner_email\nAcme,7707083893,770101001,1027700132195,owner@test.ru\n"
    rows = imp._parse_rows(csv_text)
    assert len(rows) == 1
    assert rows[0]["name"] == "Acme"
    assert rows[0]["inn"] == "7707083893"
    assert rows[0]["owner_email"] == "owner@test.ru"


def test_parse_promo_rows():
    csv_text = "name,discount_type,discount_value,code\nPromo,percent,15,SAVE15NOW\n"
    rows = imp._parse_rows(csv_text)
    assert rows[0]["discount_type"] == "percent"
    assert rows[0]["code"] == "SAVE15NOW"


@pytest.mark.asyncio
async def test_import_promocodes_csv(db):
    csv_text = "name,discount_type,discount_value,max_uses\nBulk,percent,10,50\n"
    out = await imp.import_promocodes_csv(db, csv_text)
    await db.commit()
    assert len(out["created"]) == 1
    assert out["created"][0]["code"]


@pytest.mark.asyncio
async def test_segmentation_metrics_empty(db):
    from app.services import segmentation_metrics as sm

    out = await sm.dashboard_metrics(db, days=7)
    assert out["total"] == 0
    assert out["fallback_rate"] == 0.0


def test_admin_csv_import_routes():
    from app.api.v1 import admin as adm

    paths = {getattr(r, "path", "") for r in adm.router.routes}
    assert "/companies/import-csv" in paths
    assert "/promocodes/import-csv" in paths
    assert "/segmentation/metrics" in paths
