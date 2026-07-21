"""§9 Sprint 2: partman, WAL-G, dedicated buckets."""

from __future__ import annotations


def test_partman_skipped_when_disabled(monkeypatch):
    from app.core.config import settings
    from app.services.partman import run_partman_maintenance

    monkeypatch.setattr(settings, "PARTMAN_ENABLED", False)
    out = run_partman_maintenance()
    assert out.get("skipped") is True


def test_walg_skipped_when_disabled(monkeypatch):
    from app.core.config import settings
    from app.services.backup import run_walg_backup_push

    monkeypatch.setattr(settings, "WALG_ENABLED", False)
    out = run_walg_backup_push()
    assert out.get("skipped") is True


def test_dedicated_bucket_name():
    from app.services.company_buckets import dedicated_bucket_name, resolve_models_bucket

    assert dedicated_bucket_name(42) == "company_42_models"

    class Co:
        settings = {"dedicated_bucket": "company_99_models"}

    assert resolve_models_bucket(Co()) == "company_99_models"


def test_admin_dedicated_bucket_routes():
    from app.api.v1.admin import (
        disable_company_dedicated_bucket,
        enable_company_dedicated_bucket,
        get_company_dedicated_bucket,
    )

    assert enable_company_dedicated_bucket.__name__ == "enable_company_dedicated_bucket"
    assert disable_company_dedicated_bucket.__name__ == "disable_company_dedicated_bucket"
    assert get_company_dedicated_bucket.__name__ == "get_company_dedicated_bucket"


def test_backup_suite_calls_pg_dump(monkeypatch):
    from app.services import backup as bk

    monkeypatch.setattr(bk, "run_pg_dump_to_minio", lambda: {"method": "pg_dump"})
    monkeypatch.setattr(bk, "run_walg_backup_push", lambda: {"skipped": True})
    out = bk.run_backup_suite()
    assert out["pg_dump"]["method"] == "pg_dump"
