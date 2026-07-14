"""Тесты auth API."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_register_verify_login_flow(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"

    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "password_confirm": password,
            "consents": ["terms", "privacy", "offer", "rights", "nsfw_rules"],
        },
    )
    assert reg.status_code == 201
    dev_code = reg.json()["dev_code"]
    assert dev_code is not None

    verify = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": dev_code},
    )
    assert verify.status_code == 200
    assert verify.json()["status"] == "pending_type"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh.json()["refresh_token"]},
    )
    assert logout.status_code == 200
