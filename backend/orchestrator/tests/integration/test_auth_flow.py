"""E2E auth: регистрация → верификация → логин → refresh → logout (§2).

Критический путь входа. Требует живой Postgres (схема создаётся conftest'ом).
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_register_verify_login_flow(client, unique_email):
    email = unique_email()
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
    assert reg.status_code == 201, reg.text
    dev_code = reg.json()["dev_code"]
    assert dev_code

    verify = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": dev_code},
    )
    assert verify.status_code == 200, verify.text

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    tokens = login.json()
    assert tokens.get("access_token") and tokens.get("refresh_token")

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200, refresh.text

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh.json()["refresh_token"]},
    )
    assert logout.status_code == 200, logout.text


async def test_login_wrong_password_rejected(client, unique_email):
    email = unique_email()
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
    await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": reg.json()["dev_code"]},
    )
    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password"},
    )
    assert bad.status_code in (400, 401)
