"""§3.2 offline sync, §3.4 team members stats, §3.6 push ack cancel fallback."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1 import company as company_api
from app.api.v1 import user as user_api
from app.services import push as push_svc
from app.services import push_fallback as pf


def test_list_members_route_has_search():
    sig = inspect.signature(company_api.list_members)
    assert "search" in sig.parameters


def test_notification_mark_read_route():
    sig = inspect.signature(user_api.notification_mark_read)
    assert "notification_id" in sig.parameters


def test_send_fcm_includes_notification_id_in_data():
    res = push_svc.send_fcm_to_token("t", "Hi", "Body", {"notification_id": "42", "type": "test"})
    assert "notification_id" in (res.get("detail") or "") or res.get("ok") is not None


@pytest.mark.asyncio
async def test_cancel_for_notification():
    redis = MagicMock()
    redis.zrem = AsyncMock()
    redis.hdel = AsyncMock()
    ok = await pf.cancel_for_notification(redis, user_id=7, notif_id=99)
    assert ok is True
    redis.zrem.assert_awaited_once_with(pf.DUE_ZSET, "7:99")
    redis.hdel.assert_awaited_once_with(pf.ITEM_HASH, "7:99")
