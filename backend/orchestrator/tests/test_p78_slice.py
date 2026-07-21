"""§23.2 exporters, §23.3 Tailscale, §23.5 Grafana cluster dashboards."""

from pathlib import Path

from app.services.tailscale_metrics import tailscale_status


def test_ha_tailscale_route():
    from app.api.v1 import admin as adm

    paths = {getattr(r, "path", "") for r in adm.router.routes}
    assert any("tailscale" in p for p in paths)


def test_tailscale_not_configured():
    out = tailscale_status()
    assert out["configured"] is False


def test_ha_compose_exporters():
    body = Path(__file__).resolve().parents[3] / "docker-compose.ha.yml"
    text = body.read_text(encoding="utf-8")
    assert "postgres-exporter" in text
    assert "prometheus:" in text


def test_grafana_cluster_dashboard():
    p = Path(__file__).resolve().parents[3] / "infra" / "grafana" / "dashboards" / "kwork-cluster-health.json"
    assert p.is_file()
    assert "Cluster Health" in p.read_text(encoding="utf-8")
