"""§10.4 watermark by model, §10.5 audit export list."""

from __future__ import annotations

from app.services import audit_export as ae


def test_list_exported_periods_empty(monkeypatch):
    class FakeMinio:
        def ensure_buckets(self):
            return []

        def list_objects(self, bucket, prefix=""):
            return []

    monkeypatch.setattr(ae, "minio_service", FakeMinio())
    out = ae.list_exported_periods()
    assert out["ok"] is True
    assert out["items"] == []


def test_watermark_verify_model_route():
    from app.api.v1 import watermark_admin as wa

    assert any(r.path.endswith("/verify-model/{model_uuid}") for r in wa.router.routes)
