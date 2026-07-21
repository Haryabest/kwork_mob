"""§22.2 Patroni, §22.3 Redis Sentinel, §22.5 MinIO read-failover."""

from app.core.config import settings
from app.services.minio_replication import replication_status
from app.services.patroni_status import patroni_status
from app.services.redis_sentinel_status import redis_sentinel_status


def test_ha_patroni_route():
    from app.api.v1 import admin as adm

    paths = {getattr(r, "path", "") for r in adm.router.routes}
    assert any("patroni-status" in p for p in paths)


def test_patroni_status_offline(monkeypatch):
    def _fail(*_a, **_k):
        raise OSError("unreachable")

    monkeypatch.setattr("app.services.patroni_status.httpx.Client", _fail)
    out = patroni_status()
    assert out["ok"] is False
    assert "error" in out


def test_redis_sentinel_not_configured():
    out = redis_sentinel_status()
    assert "configured" in out


def test_minio_replica_config(monkeypatch):
    monkeypatch.setattr(settings, "MINIO_REPLICA_ENDPOINT", "http://minio-2:9000")
    monkeypatch.setattr(
        "app.services.minio_replication.minio_service.smart",
        lambda: {"ok": True, "cluster_ha": {}, "alert_replication_failed": False},
    )
    out = replication_status()
    assert out["read_failover"] is True
