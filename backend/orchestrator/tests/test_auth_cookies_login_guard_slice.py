"""Auth cookies + login guard slice tests."""

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from app.services import auth_cookies as ac
from app.services import login_guard as lg


def test_web_cookie_auth_origin(monkeypatch):
    from fastapi import Request

    monkeypatch.setattr(ac.settings, "CORS_ORIGINS", ["http://localhost:3000"])
    scope = {"type": "http", "headers": [(b"origin", b"http://localhost:3000")]}
    req = Request(scope)
    assert ac.web_cookie_auth(req) is True


def test_set_and_clear_cookies():
    resp = Response()
    ac.set_auth_cookies(resp, access="a", refresh="r", remember_me=True)
    assert any(h[0].lower() == b"set-cookie" for h in resp.raw_headers)
    ac.clear_auth_cookies(resp)


@pytest.mark.asyncio
async def test_login_status_requires_captcha_after_failures(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.data: dict[str, int] = {}

        async def get(self, key):
            return self.data.get(key)

        async def incr(self, key):
            self.data[key] = int(self.data.get(key, 0)) + 1
            return self.data[key]

        async def expire(self, *_a, **_k):
            return True

        async def set(self, key, val, ex=None):
            self.data[key] = val

        async def delete(self, *keys):
            for k in keys:
                self.data.pop(k, None)

    fake = FakeRedis()

    async def fake_get_redis():
        return fake

    monkeypatch.setattr(lg, "get_redis", fake_get_redis)

    for _ in range(5):
        await lg.record_login_failure("1.2.3.4", "u@test.ru")
    st = await lg.login_status("1.2.3.4", "u@test.ru")
    assert st["requires_captcha"] is True
    assert st["blocked"] is True


@pytest.mark.asyncio
async def test_require_captcha_raises_without_token(monkeypatch):
    class FakeRedis:
        async def get(self, key):
            if key.startswith(lg.LOGIN_BLOCK_PREFIX):
                return None
            return b"5"

        async def incr(self, key):
            return 5

        async def expire(self, *_a, **_k):
            return True

        async def set(self, *_a, **_k):
            return True

        async def delete(self, *_a, **_k):
            return True

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr(lg, "get_redis", fake_get_redis)

    with pytest.raises(HTTPException) as exc:
        await lg.require_captcha_if_needed("1.2.3.4", "u@test.ru", None)
    assert exc.value.status_code == 429
    assert exc.value.detail["requires_captcha"] is True


@pytest.mark.asyncio
async def test_verify_recaptcha_skips_in_dev(monkeypatch):
    monkeypatch.setattr(lg.settings, "RECAPTCHA_SECRET_KEY", "")
    monkeypatch.setattr(lg.settings, "ENVIRONMENT", "development")
    await lg.verify_recaptcha("token", "127.0.0.1")
