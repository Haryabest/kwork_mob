"""Sprint 5: Debezium PG→CH, marketplace auto-upload."""

from __future__ import annotations

import asyncio


def test_debezium_status_offline():
    from app.services.debezium_status import debezium_status

    out = debezium_status()
    assert "sync_mode" in out
    assert out["configured"] is False


def test_user_events_sync_skips_debezium_mode(monkeypatch):
    from app.services import user_events_sync as ues

    monkeypatch.setattr("app.core.config.settings.USER_EVENTS_SYNC_MODE", "debezium")

    class _Db:
        async def scalar(self, *_a, **_k):
            return 3

    out = asyncio.run(ues.sync_unsynced(_Db()))
    assert out.get("skipped") == "debezium"
    assert out["pending"] == 3


def test_marketplace_auto_upload_schedule_disabled(monkeypatch):
    from types import SimpleNamespace

    from app.services.marketplace_auto_upload import schedule_after_generation

    monkeypatch.setattr(
        "app.services.marketplace_auto_upload.settings.MARKETPLACE_UPLOAD_ENABLED", False
    )
    order = SimpleNamespace(id=1, target_marketplace="wb")
    out = schedule_after_generation(order=order, model_uuid="m1", payload={})
    assert out["scheduled"] is False


def test_resolve_sku_fallback():
    from types import SimpleNamespace

    from app.services.marketplace_auto_upload import resolve_sku

    order = SimpleNamespace(id=42)
    assert resolve_sku(order=order, payload={}) == "42"
    assert resolve_sku(order=order, payload={"sku": "ABC-1"}) == "ABC-1"


def test_ha_readiness_debezium_check():
    from app.services.ha_readiness import ha_readiness

    out = ha_readiness()
    assert "debezium_configured" in out["checks"]


def test_admin_debezium_route():
    from app.api.v1.admin import monitoring_debezium_status

    assert monitoring_debezium_status.__name__ == "monitoring_debezium_status"
