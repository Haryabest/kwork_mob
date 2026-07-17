"""Integration smoke: models filters + trash pagination §19.9 / §3.3.1."""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _login(client, unique_email):
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
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_user_models_filters_and_trash_pagination(client, unique_email):
    headers = await _login(client, unique_email)

    models = await client.get(
        "/api/v1/user/models",
        headers=headers,
        params={"limit": 5, "offset": 0, "sort": "newest", "publish_filter": "draft"},
    )
    assert models.status_code == 200
    body = models.json()
    assert "items" in body
    assert "total" in body
    assert body["limit"] == 5
    assert body["offset"] == 0

    trash = await client.get(
        "/api/v1/models/trash",
        headers=headers,
        params={"limit": 10, "offset": 0},
    )
    assert trash.status_code == 200
    t = trash.json()
    assert "items" in t
    assert "total" in t
    assert t["limit"] == 10

    analytics = await client.post(
        "/api/v1/user/analytics/events",
        headers=headers,
        json={
            "events": [
                {
                    "event": "screen_view",
                    "ts": "2026-07-17T10:00:00Z",
                    "props": {"screen": "integration_smoke"},
                }
            ]
        },
    )
    assert analytics.status_code == 200
    assert analytics.json().get("accepted") == 1
