"""User audit CSV export slice §2.5.5."""

import inspect

import pytest

from app.api.v1.user import user_audit_export
from app.models import AuditLog, User


def test_user_audit_export_route_exists():
    sig = inspect.signature(user_audit_export)
    assert "user" in sig.parameters
    assert "db" in sig.parameters


@pytest.mark.asyncio
async def test_user_audit_export_csv_body():

    row = AuditLog(
        id=2,
        user_id=5,
        action="oauth_login",
        details={"provider": "yandex"},
        created_at=None,
    )

    class FakeDb:
        async def scalar(self, _stmt):
            return 1

        async def scalars(self, _stmt):
            class R:
                def all(self):
                    return [row]

            return R()

    user = User(id=5, email="u@example.com")
    resp = await user_audit_export(user=user, db=FakeDb(), action_prefix="oauth_", days=30)
    body = resp.body.decode("utf-8")
    assert "oauth_login" in body
    assert "id,user_id,action,details,created_at" in body.splitlines()[0]
