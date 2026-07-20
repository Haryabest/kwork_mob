"""access_log CSV slice §10.7.2."""

import pytest

from app.services import access_log as al


def test_access_log_to_csv():
    body = al.to_csv(
        [
            {
                "id": 1,
                "timestamp": "2026-07-20T12:00:00+00:00",
                "user_id": 7,
                "company_id": 2,
                "model_uuid": "abc-123",
                "action": "download",
                "file_format": "glb",
                "ip_address": "1.2.3.4",
            }
        ]
    ).decode("utf-8-sig")
    lines = body.strip().splitlines()
    assert "model_uuid" in lines[0]
    assert "download" in lines[1]
    assert "abc-123" in lines[1]


@pytest.mark.asyncio
async def test_list_user_access_logs():
    from app.models import AccessLog

    row = AccessLog(id=1, user_id=3, model_uuid="uuid-1", action="download", file_format="glb")

    class FakeDb:
        async def scalar(self, _stmt):
            return 1

        async def scalars(self, _stmt):
            class R:
                def all(self_inner):
                    return [row]

            return R()

    data = await al.list_access_logs(FakeDb(), user_id=3, limit=10)
    assert data["total"] == 1
    assert data["items"][0]["action"] == "download"
