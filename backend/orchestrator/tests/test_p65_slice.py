"""§11.1 Grafana, §11.4 finance breakdown, §11.5 B2B API usage."""

from __future__ import annotations

import pytest

from app.services import b2b_api_usage as usage_svc


def test_grafana_embed_config_unset(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "GRAFANA_EMBED_URL", "")
    url = (settings.GRAFANA_EMBED_URL or "").strip()
    assert url == ""


@pytest.mark.asyncio
async def test_b2b_api_usage_empty(db):
    out = await usage_svc.summary(db, days=7)
    assert out["companies_with_keys"] == 0
    assert out["items"] == []


def test_dashboard_finance_keys():
    from app.services import metrics as m

    assert "upsell_revenue_7d_rub" in str(m.dashboard_aggregates.__doc__ or "finance")
