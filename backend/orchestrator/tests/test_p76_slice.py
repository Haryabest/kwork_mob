"""§22.4 ClickHouse HA compose, §23.4 cluster health, §23.1 node_exporter."""

from pathlib import Path

from app.services.storage_cluster_health import storage_cluster_health


def test_cluster_health_route():
    from app.api.v1 import admin as adm

    paths = {getattr(r, "path", "") for r in adm.router.routes}
    assert any("cluster-health" in p for p in paths)


def test_cluster_health_two_nodes(monkeypatch):
    monkeypatch.setattr(
        "app.services.storage_cluster_health.minio_service.smart",
        lambda: {
            "ok": True,
            "cluster_ha": {"nodes": [], "postgres": {}, "minio_replication": []},
            "smart_disks": [],
            "alert_replication_failed": False,
            "alert_disk_critical": False,
            "used_percent": 10,
        },
    )
    out = storage_cluster_health()
    assert len(out.get("nodes") or []) == 2


def test_ha_compose_clickhouse():
    text = Path(__file__).resolve().parents[3] / "docker-compose.ha.yml"
    body = text.read_text(encoding="utf-8")
    assert "clickhouse-keeper" in body
    assert "node-exporter-a" in body
