"""OAuth providers + auth slice."""

import pytest
from fastapi import HTTPException

from app.services import oauth_auth as oa
from app.services import oauth_providers as op


def test_list_enabled_providers_empty(monkeypatch):
    monkeypatch.setattr(op.settings, "OAUTH_VK_CLIENT_ID", "")
    monkeypatch.setattr(op.settings, "OAUTH_YANDEX_CLIENT_ID", "")
    monkeypatch.setattr(op.settings, "OAUTH_SBER_CLIENT_ID", "")
    assert op.list_enabled_providers() == []


def test_list_enabled_providers_vk(monkeypatch):
    monkeypatch.setattr(op.settings, "OAUTH_VK_CLIENT_ID", "vk-id")
    monkeypatch.setattr(op.settings, "OAUTH_VK_CLIENT_SECRET", "secret")
    monkeypatch.setattr(op.settings, "OAUTH_YANDEX_CLIENT_ID", "")
    monkeypatch.setattr(op.settings, "OAUTH_SBER_CLIENT_ID", "")
    items = op.list_enabled_providers()
    assert len(items) == 1
    assert items[0]["provider"] == "vk"


def test_parse_profile_yandex():
    uid, email, name = op.parse_profile(
        "yandex",
        {"id": "123", "default_email": "u@yandex.ru", "real_name": "Test User"},
    )
    assert uid == "123"
    assert email == "u@yandex.ru"
    assert "Test" in name


def test_build_authorize_url():
    cfg = op.OAuthProviderConfig(
        key="yandex",
        label="Yandex",
        client_id="cid",
        client_secret="sec",
        authorize_url="https://oauth.yandex.ru/authorize",
        token_url="https://oauth.yandex.ru/token",
        userinfo_url="https://login.yandex.ru/info",
        scope="login:email",
        extra_authorize={},
    )
    url = op.build_authorize_url(cfg, redirect_uri="http://localhost/cb", state="abc")
    assert "client_id=cid" in url
    assert "state=abc" in url


@pytest.mark.asyncio
async def test_start_oauth_unknown_provider():
    with pytest.raises(HTTPException) as exc:
        await oa.start_oauth("google", redirect_uri=None, platform="web", mode="login", consents=None)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_start_oauth_register_requires_consents(monkeypatch):
    monkeypatch.setattr(op.settings, "OAUTH_YANDEX_CLIENT_ID", "yid")
    monkeypatch.setattr(op.settings, "OAUTH_YANDEX_CLIENT_SECRET", "ysec")

    class FakeRedis:
        async def set(self, *_a, **_k):
            return True

    async def fake_redis():
        return FakeRedis()

    monkeypatch.setattr("app.services.oauth_auth.get_redis", fake_redis)

    with pytest.raises(HTTPException) as exc:
        await oa.start_oauth("yandex", redirect_uri=None, platform="web", mode="register", consents=["terms"])
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_start_oauth_link(monkeypatch):
    monkeypatch.setattr(op.settings, "OAUTH_VK_CLIENT_ID", "vk")
    monkeypatch.setattr(op.settings, "OAUTH_VK_CLIENT_SECRET", "sec")

    class FakeRedis:
        stored = None

        async def set(self, key, val, ex=None):
            self.stored = val

    fake = FakeRedis()

    async def fake_redis():
        return fake

    monkeypatch.setattr("app.services.oauth_auth.get_redis", fake_redis)
    data = await oa.start_oauth_link(42, "vk", redirect_uri="http://cb", platform="web")
    assert "authorize_url" in data
    assert "vk" in data["authorize_url"]
