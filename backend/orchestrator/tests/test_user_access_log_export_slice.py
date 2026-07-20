"""User access-log CSV export slice §2.5.5."""

import inspect

import pytest

from app.api.v1.user import user_access_log_export
from app.models import User


def test_user_access_log_export_route_exists():
    sig = inspect.signature(user_access_log_export)
    assert "user" in sig.parameters
    assert "db" in sig.parameters


@pytest.mark.asyncio
async def test_user_access_log_export_returns_csv():
    class FakeDb:
        async def scalars(self, _stmt):
            class R:
                def all(self):
                    return []

            return R()

        async def scalar(self, _stmt):
            return 0

    user = User(id=3, email="u@example.com")
    resp = await user_access_log_export(user=user, db=FakeDb())
    body = resp.body.decode("utf-8-sig")
    assert "model_uuid" in body.splitlines()[0]
