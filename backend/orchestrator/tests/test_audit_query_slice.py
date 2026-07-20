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


@pytest.mark.asyncio
async def test_list_company_audit_logs_oauth_members():
    from app.models import AuditLog

    oauth_row = AuditLog(
        id=2,
        user_id=5,
        company_id=None,
        action="oauth_link",
        details={"provider": "yandex"},
    )
    corp_row = AuditLog(
        id=3,
        user_id=5,
        company_id=1,
        action="company_invite_sent",
        details={},
    )

    class FakeDbOauth:
        async def scalar(self, _stmt):
            return 1

        async def scalars(self, _stmt):
            class R:
                def all(self_inner):
                    return [oauth_row]

            return R()

    class FakeDbCorp:
        async def scalar(self, _stmt):
            return 1

        async def scalars(self, _stmt):
            class R:
                def all(self_inner):
                    return [corp_row]

            return R()

    data = await aq.list_company_audit_logs(
        FakeDbOauth(), company_id=1, member_user_ids=[5], action_prefix="oauth_", days=30
    )
    assert data["items"][0]["action"] == "oauth_link"

    data2 = await aq.list_company_audit_logs(FakeDbCorp(), company_id=1, member_user_ids=[5], days=30)
    assert data2["total"] == 1


@pytest.mark.asyncio
async def test_list_user_audit_logs_oauth():
    from app.models import AuditLog

    row = AuditLog(id=3, user_id=7, action="oauth_unlink", details={"provider": "vk"})

    class FakeDb:
        async def scalar(self, _stmt):
            return 1

        async def scalars(self, _stmt):
            class R:
                def all(self_inner):
                    return [row]

            return R()

    data = await aq.list_audit_logs(FakeDb(), user_id=7, action_prefix="oauth_", days=30)
    assert data["items"][0]["action"] == "oauth_unlink"
    assert data["items"][0]["user_id"] == 7


@pytest.mark.asyncio
async def test_user_audit_export_rows():
    import csv
    import io

    from app.models import AuditLog

    row = AuditLog(
        id=4,
        user_id=7,
        action="oauth_unlink",
        details={"provider": "vk"},
        created_at=None,
    )

    class FakeDb:
        async def scalar(self, _stmt):
            return 1

        async def scalars(self, _stmt):
            class R:
                def all(self_inner):
                    return [row]

            return R()

    data = await aq.list_audit_logs(FakeDb(), user_id=7, action="oauth_unlink", days=30, limit=5000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "user_id", "action", "details", "created_at"])
    for r in data["items"]:
        w.writerow([r["id"], r["user_id"], r["action"], r["details"], r["created_at"] or ""])
    lines = buf.getvalue().strip().splitlines()
    assert lines[0] == "id,user_id,action,details,created_at"
    assert "oauth_unlink" in lines[1]
    assert "vk" in lines[1]
