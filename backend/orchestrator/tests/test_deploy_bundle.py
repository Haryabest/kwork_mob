"""Deploy bundle export (§15.3 / §20)."""

from app.services import deploy_bundle as db


def test_worker_bundle_shape():
    b = db.worker_bundle(worker_id="w-test")
    assert b["role"] == "worker"
    assert b["env"]["WORKER_ID"] == "w-test"
    assert "bootstrap_sh" in b
    assert "docker run" in b["run_example"]


def test_storage_primary():
    b = db.storage_bundle(node="primary")
    assert b["role"] == "storage"
    assert b["node"] == "primary"
    assert "docker-compose.ha.yml" in b["compose_file"]


def test_build_all():
    b = db.build_bundle("all")
    assert "bundles" in b
    assert "worker" in b["bundles"]
    assert "cloud_gpu" in b["bundles"]
