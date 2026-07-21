"""Sprint 6: mesh, HA cutover, CSE KMS, queue heal."""

from __future__ import annotations

import pytest


def test_mesh_status_offline():
    from app.services.mesh_hosts import mesh_status

    out = mesh_status()
    assert "configured" in out
    assert out["configured"] is False


def test_cutover_preflight(monkeypatch):
    monkeypatch.setattr(
        "app.services.ha_cutover.minio_service.smart",
        lambda: {"ok": True, "cluster_ha": {}},
    )
    monkeypatch.setattr(
        "app.services.ha_cutover.witness_status",
        lambda: {"ok": True, "url": "http://witness"},
    )
    from app.services.ha_cutover import cutover_preflight

    out = cutover_preflight()
    assert "checks" in out
    assert len(out["checks"]) >= 5


def test_cse_policy_defaults():
    from app.services.cse_kms import cse_policy

    assert cse_policy(None) == {}


@pytest.mark.asyncio
async def test_dequeue_empty_redis_skips_pg(db, monkeypatch):
    from app.services.queue import queue_service

    async def empty():
        return None

    pg_called = False

    async def pg_dequeue(_db):
        nonlocal pg_called
        pg_called = True
        return None

    monkeypatch.setattr(queue_service, "dequeue", empty)
    monkeypatch.setattr(queue_service, "dequeue_from_postgres", pg_dequeue)
    item = await queue_service.dequeue_with_fallback(db)
    assert item is None
    assert pg_called is False


def test_admin_ha_routes():
    from app.api.v1.admin import ha_cutover_preflight, ha_mesh_status

    assert ha_mesh_status.__name__ == "ha_mesh_status"
    assert ha_cutover_preflight.__name__ == "ha_cutover_preflight"


def test_worker_cse_route():
    from app.api.v1.worker_callback import worker_cse_key

    assert worker_cse_key.__name__ == "worker_cse_key"
