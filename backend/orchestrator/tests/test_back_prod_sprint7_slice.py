"""Sprint 7: DoD export, TRELLIS status, MinIO VIP."""

from __future__ import annotations

import pytest


def test_dod_to_csv():
    from app.services.dod_export import dod_to_csv

    csv_text = dod_to_csv(
        {
            "period_days": 7,
            "since": "2026-01-01",
            "summary": {"passed": 8, "total": 11, "ready": True},
            "checks": [{"metric": "success_rate", "value": 0.96, "pass": True}],
            "raw": {"completed_orders": 100},
        }
    )
    assert "success_rate" in csv_text
    assert "completed_orders" in csv_text


@pytest.mark.asyncio
async def test_trellis_prod_status_empty(db):
    from app.services.trellis_prod_status import trellis_prod_status

    out = await trellis_prod_status(db)
    assert out["workers_total"] == 0
    assert out["production_ready"] is False


def test_minio_vip_not_configured(monkeypatch):
    from app.core.config import settings
    from app.services.minio_vip_status import minio_vip_status

    monkeypatch.setattr(settings, "MINIO_VIP", "")
    monkeypatch.setattr(settings, "MINIO_ENDPOINT", "http://127.0.0.1:1")
    out = minio_vip_status()
    assert out["configured"] is False


def test_admin_sprint7_routes():
    from app.api.v1.admin import (
        dod_metrics_export,
        ha_minio_vip_status,
        worker_trellis_status,
    )

    assert dod_metrics_export.__name__ == "dod_metrics_export"
    assert worker_trellis_status.__name__ == "worker_trellis_status"
    assert ha_minio_vip_status.__name__ == "ha_minio_vip_status"
