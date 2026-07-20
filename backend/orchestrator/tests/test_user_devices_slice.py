"""User devices list slice §2.5.5."""

import inspect

import pytest
from fastapi import HTTPException

from app.api.v1.user import delete_device_by_id, list_devices
from app.models import DeviceToken, User


def test_list_devices_route_exists():
    sig = inspect.signature(list_devices)
    assert "user" in sig.parameters
    assert "db" in sig.parameters


def test_delete_device_by_id_route_exists():
    sig = inspect.signature(delete_device_by_id)
    assert "device_id" in sig.parameters


@pytest.mark.asyncio
async def test_list_devices_masks_token():
    row = DeviceToken(
        id=1,
        user_id=3,
        token="abcdefghijklmnop",
        platform="android",
        app_version="1.0.0",
    )

    class FakeDb:
        async def scalars(self, _stmt):
            class R:
                def all(self):
                    return [row]

            return R()

    user = User(id=3, email="u@example.com")
    out = await list_devices(user=user, db=FakeDb())
    assert len(out["items"]) == 1
    assert out["items"][0]["token_prefix"] == "abcdefghijkl…"
    assert out["items"][0]["platform"] == "android"


@pytest.mark.asyncio
async def test_delete_device_by_id_not_found():
    class FakeDb:
        async def scalar(self, _stmt):
            return None

    user = User(id=3, email="u@example.com")
    with pytest.raises(HTTPException) as exc:
        await delete_device_by_id(device_id=99, user=user, db=FakeDb())
    assert exc.value.status_code == 404
