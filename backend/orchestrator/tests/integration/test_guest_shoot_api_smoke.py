"""Integration smoke: guest shoot link API §3.15."""

import base64

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_MIN_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "2wBDAf//////////////////////////////////////////////////////////////////////////////////////"
    "wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/"
    "9oADAMBAAIQAxAAAAGfAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAQUCf//EABQRAQAAAAAAAAAA"
    "AAAAAAAAAAD/2gAIAQMBAT8Bf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQIBAT8Bf//EABQQAQAAAAAA"
    "AAAAAAAAAAAAAAD/2gAIAQEABj8Cf//Z"
)


async def _login_owner(client, unique_email):
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


async def test_guest_shoot_link_flow(client, unique_email):
    headers = await _login_owner(client, unique_email)

    link = await client.post(
        "/api/v1/company/shoot_link",
        headers=headers,
        json={"category": "other", "tier": "small", "ttl_hours": 48, "max_uses": 1},
    )
    assert link.status_code == 200
    token = link.json()["url"].rstrip("/").split("/")[-1]

    shoot = await client.get(f"/api/v1/shoot/{token}")
    if shoot.status_code == 503:
        pytest.skip("MinIO unavailable")
    assert shoot.status_code == 200
    uploads = shoot.json()["uploads"]
    assert len(uploads) == 12

    files = [("files", (f"view_{i:02d}.jpg", _MIN_JPEG, "image/jpeg")) for i in range(12)]
    uploaded = await client.post(f"/api/v1/shoot/{token}/upload", files=files)
    if uploaded.status_code == 503:
        pytest.skip("MinIO unavailable")
    assert uploaded.status_code == 200
    assert uploaded.json().get("link_used") is True
