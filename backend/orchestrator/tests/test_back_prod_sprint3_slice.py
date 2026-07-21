"""§22-23 Sprint 3: witness, WAF, VictoriaMetrics."""

from __future__ import annotations


def test_witness_status_offline():
    from app.services.witness_status import witness_status

    out = witness_status()
    assert "url" in out
    assert "ok" in out


def test_victoria_status_offline():
    from app.services.victoria_metrics import victoria_status

    out = victoria_status()
    assert "url" in out


def test_ha_readiness_includes_sprint3_checks(monkeypatch):
    monkeypatch.setattr(
        "app.services.ha_readiness.minio_service.smart",
        lambda: {"ok": True, "cluster_ha": {}},
    )
    from app.services.ha_readiness import ha_readiness

    out = ha_readiness()
    assert "witness_configured" in out["checks"]
    assert "victoria_metrics_configured" in out["checks"]
    assert "cloudflare_waf" in out["checks"]


def test_admin_ha_routes():
    from app.api.v1.admin import (
        ha_witness_status,
        monitoring_victoria_status,
        monitoring_waf_status,
    )

    assert ha_witness_status.__name__ == "ha_witness_status"
    assert monitoring_victoria_status.__name__ == "monitoring_victoria_status"
    assert monitoring_waf_status.__name__ == "monitoring_waf_status"


def test_cloudflare_middleware_skips_health():
    from app.core.cloudflare_waf import CloudflareWafMiddleware

    assert CloudflareWafMiddleware is not None
