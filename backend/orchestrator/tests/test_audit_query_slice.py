"""Admin audit_log query slice."""

import pytest

from app.services import audit_query as aq


@pytest.mark.asyncio
async def test_oauth_audit_summary_empty():
    class FakeDb:
        async def scalar(self, _stmt):
            return 0

    data = await aq.oauth_audit_summary(FakeDb(), days=7)
    assert data["days"] == 7
    assert data["oauth_login"] == 0
    assert data["oauth_link"] == 0
    assert data["oauth_unlink"] == 0
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_audit_logs_oauth_prefix():
    from app.models import AuditLog

    row = AuditLog(
        id=1,
        user_id=9,
        action="oauth_login",
        details={"provider": "vk", "platform": "web"},
    )

    class FakeDb:
        async def scalar(self, _stmt):
            return 1

        async def scalars(self, _stmt):
            class R:
                def all(self_inner):
                    return [row]

            return R()

    data = await aq.list_audit_logs(FakeDb(), action_prefix="oauth_", days=30, limit=10)
    assert data["total"] == 1
    assert data["items"][0]["action"] == "oauth_login"
    assert data["items"][0]["details"]["provider"] == "vk"
