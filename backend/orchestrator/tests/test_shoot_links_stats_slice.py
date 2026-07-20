"""Shoot links stats slice §3.15.4."""

from types import SimpleNamespace

import pytest

from app.services import shoot_links as sl


@pytest.mark.asyncio
async def test_company_stats_counts():
    rows = [
        SimpleNamespace(
            id=1,
            status="active",
            used_count=0,
            token="tok1",
            task_uuid="u1",
            max_uses=1,
            category="other",
            tier="small",
            expires_at=None,
            created_at=None,
        ),
        SimpleNamespace(
            id=2,
            status="used",
            used_count=1,
            token="tok2",
            task_uuid="u2",
            max_uses=1,
            category="other",
            tier="small",
            expires_at=None,
            created_at=None,
        ),
        SimpleNamespace(
            id=3,
            status="expired",
            used_count=0,
            token="tok3",
            task_uuid="u3",
            max_uses=1,
            category="other",
            tier="small",
            expires_at=None,
            created_at=None,
        ),
    ]

    class FakeDb:
        def __init__(self):
            self._calls = 0

        async def scalars(self, _stmt):
            self._calls += 1
            call = self._calls

            class R:
                def all(self_inner):
                    return [] if call == 1 else rows

            return R()

        async def flush(self):
            return None

    data = await sl.company_stats(FakeDb(), company_id=1)
    assert data["created"] == 3
    assert data["success"] == 1
    assert data["conversion_rate"] == round(1 / 3, 4)
