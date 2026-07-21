"""§14.4 MinIO replication, §15.3 email templates, §20.7 React Query deps."""

from app.services.email_templates import render_template, templates_root
from app.services.minio_replication import replication_status


def test_minio_replication_routes():
    from app.api.v1 import admin as adm

    paths = {getattr(r, "path", "") for r in adm.router.routes}
    assert any("minio-replication" in p for p in paths)


def test_replication_status_shape(monkeypatch):
    monkeypatch.setattr(
        "app.services.minio_replication.minio_service.smart",
        lambda: {"ok": True, "cluster_ha": {}, "alert_replication_failed": False},
    )
    out = replication_status()
    assert "buckets" in out
    assert "setup_script" in out


def test_email_templates_from_disk():
    root = templates_root()
    assert root.is_dir()
    data = render_template("verification", "ru", code="123456", minutes=10)
    assert "123456" in data["body"]
    assert (root / "ru" / "verification.json").is_file()
