"""§20.8 global queue WS, §20.9 polish, §22.1 HA readiness."""

from pathlib import Path

from app.services.ha_readiness import ha_readiness


def test_ha_readiness_route():
    from app.api.v1 import admin as adm

    paths = {getattr(r, "path", "") for r in adm.router.routes}
    assert any("ha/readiness" in p for p in paths)


def test_ha_readiness_shape(monkeypatch):
    monkeypatch.setattr(
        "app.services.ha_readiness.minio_service.smart",
        lambda: {
            "ok": True,
            "cluster_ha": {"postgres": {"role": "primary"}},
            "alert_replication_failed": False,
            "alert_disk_critical": False,
        },
    )
    out = ha_readiness()
    assert "checks" in out
    assert "score" in out


def test_queue_ws_context_file():
  p = Path(__file__).resolve().parents[3] / "apps" / "web-seller" / "src" / "context" / "QueueWsContext.tsx"
  assert p.is_file()
  assert "QueueWsProvider" in p.read_text(encoding="utf-8")
