"""Company audit CSV export slice §2.5.5."""

import inspect

import pytest

from app.api.v1.company import audit_export


def test_company_audit_export_route_exists():
    sig = inspect.signature(audit_export)
    assert "user" in sig.parameters
    assert "db" in sig.parameters
    assert "days" in sig.parameters
