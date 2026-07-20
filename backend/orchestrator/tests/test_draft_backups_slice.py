"""Draft backups list slice §3.3.2."""

import inspect

from app.api.v1.user import delete_draft_backup, list_draft_backups
from app.services import draft_backup as dbk


def test_list_draft_backups_route_exists():
    sig = inspect.signature(list_draft_backups)
    assert "user" in sig.parameters


def test_delete_draft_backup_route_exists():
    sig = inspect.signature(delete_draft_backup)
    assert "model_uuid" in sig.parameters


def test_draft_backup_ttl_days():
    assert dbk.TTL_DAYS == 7


def test_delete_backup_function_exists():
    assert callable(dbk.delete_backup)
