"""Smoke API paths used by mobile client (§3.4 / §19)."""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_mobile_auth_and_user_paths(client, unique_email):
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
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/user/me", headers=headers)
    assert me.status_code == 200

    device = await client.post(
        "/api/v1/user/devices",
        headers=headers,
        json={"token": "f" * 140, "platform": "android", "app_version": "0.1.0"},
    )
    assert device.status_code in (200, 201)

    banners = await client.get("/api/v1/user/campaign_banners", headers=headers)
    assert banners.status_code == 200
    assert "items" in banners.json()

    analytics = await client.post(
        "/api/v1/user/analytics/events",
        headers=headers,
        json={
            "events": [
                {
                    "event": "screen_view",
                    "ts": "2026-01-01T00:00:00Z",
                    "props": {"screen": "home"},
                }
            ]
        },
    )
    assert analytics.status_code == 200
    assert analytics.json().get("accepted") == 1
