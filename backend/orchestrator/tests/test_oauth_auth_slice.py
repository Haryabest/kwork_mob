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


@pytest.mark.asyncio
async def test_unlink_oauth_blocks_last_login_method():
    from app.models import User, UserOAuthIdentity

    user = User(id=1, email="u@test.ru", password_hash=None)
    identity = UserOAuthIdentity(
        id=1, user_id=1, provider="vk", provider_user_id="123", email="u@test.ru"
    )

    class FakeDb:
        def __init__(self):
            self._call = 0

        async def scalar(self, _stmt):
            self._call += 1
            return identity if self._call == 1 else None

        async def delete(self, _obj):
            pass

        async def commit(self):
            pass

    with pytest.raises(HTTPException) as exc:
        await oa.unlink_oauth(FakeDb(), user, "vk")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_audit_oauth_login():
    added = []

    class FakeDb:
        async def commit(self):
            pass

        def add(self, row):
            added.append(row)

    await oa._audit_oauth(FakeDb(), user_id=5, action="oauth_login", provider="vk", platform="mobile")
    assert len(added) == 1
    assert added[0].action == "oauth_login"
    assert added[0].user_id == 5
    assert added[0].details == {"provider": "vk", "platform": "mobile"}


@pytest.mark.asyncio
async def test_audit_oauth_with_company_id():
    added = []

    class FakeDb:
        async def commit(self):
            pass

        def add(self, row):
            added.append(row)

    await oa._audit_oauth(
        FakeDb(), user_id=3, action="oauth_link", provider="vk", company_id=9
    )
    assert added[0].company_id == 9


@pytest.mark.asyncio
async def test_resolve_oauth_company_id_member():
    class FakeDb:
        async def scalar(self, _stmt):
            return 1

    cid = await oa._resolve_oauth_company_id(FakeDb(), user_id=2, company_id=5)
    assert cid == 5


@pytest.mark.asyncio
async def test_unlink_oauth_writes_audit():
    from app.models import User, UserOAuthIdentity

    user = User(id=1, email="u@test.ru", password_hash="hash")
    identity = UserOAuthIdentity(
        id=1, user_id=1, provider="vk", provider_user_id="123", email="u@test.ru"
    )
    added = []

    class FakeDb:
        def __init__(self):
            self._call = 0

        async def scalar(self, _stmt):
            self._call += 1
            return identity if self._call == 1 else 1

        def add(self, row):
            added.append(row)

        async def delete(self, _obj):
            pass

        async def commit(self):
            pass

    result = await oa.unlink_oauth(FakeDb(), user, "vk")
    assert result == {"unlinked": True, "provider": "vk"}
    assert any(r.action == "oauth_unlink" for r in added)


@pytest.mark.asyncio
async def test_record_screen_event_oauth():
    from app.services.analytics_ingest import record_screen_event

    added = []

    class FakeDb:
        async def flush(self):
            pass

        def add(self, row):
            added.append(row)

    await record_screen_event(FakeDb(), user_id=7, screen="oauth_login_vk")
    assert len(added) == 1
    assert added[0].props["screen"] == "oauth_login_vk"
    assert added[0].props["source"] == "server"
