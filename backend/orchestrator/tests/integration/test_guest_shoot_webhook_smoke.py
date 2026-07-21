"""Guest shoot → shoot_link.uploaded webhook §3.15 / §14.5.4."""

import base64

import pytest

from .conftest import login_owner_with_company

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_MIN_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "2wBDAf//////////////////////////////////////////////////////////////////////////////////////"
    "wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/"
    "9oADAMBAAIQAxAAAAGfAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAQUCf//EABQRAQAAAAAAAAAA"
    "AAAAAAAAAAD/2gAIAQMBAT8Bf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQIBAT8Bf//EABQQAQAAAAAA"
    "AAAAAAAAAAAAAAD/2gAIAQEABj8Cf//Z"
)


async def test_guest_shoot_webhook_delivered(client, unique_email, monkeypatch):
    captured: list[dict] = []

    async def _fake_deliver(hook, delivery):
        captured.append(
            {
                "event": delivery.event,
                "url": hook.url,
                "payload": delivery.payload,
            }
        )
        delivery.ok = True
        delivery.status_code = 200
        return True

    monkeypatch.setattr(
        "app.services.company_webhooks._deliver_once",
        _fake_deliver,
    )

    headers = await login_owner_with_company(client, unique_email)

    wh = await client.post(
        "/api/v1/company/webhooks",
        headers=headers,
        json={
            "url": "https://staging-hooks.example/webhook",
            "events": ["shoot_link.uploaded"],
            "secret": "test-secret",
        },
    )
    assert wh.status_code == 200

    link = await client.post(
        "/api/v1/company/shoot_link",
        headers=headers,
        json={"category": "other", "tier": "small", "ttl_hours": 48, "max_uses": 1},
    )
    assert link.status_code == 200
    token = link.json()["url"].rstrip("/").split("/")[-1]

    files = [("files", (f"view_{i:02d}.jpg", _MIN_JPEG, "image/jpeg")) for i in range(12)]
    uploaded = await client.post(f"/api/v1/shoot/{token}/upload", files=files)
    if uploaded.status_code == 503:
        pytest.skip("MinIO unavailable")
    assert uploaded.status_code == 200

    assert any(c["event"] == "shoot_link.uploaded" for c in captured)
    payload = next(c["payload"] for c in captured if c["event"] == "shoot_link.uploaded")
    assert payload["event"] == "shoot_link.uploaded"
    assert payload["data"]["token"] == token

    deliveries = await client.get("/api/v1/company/webhooks/deliveries", headers=headers)
    assert deliveries.status_code == 200
    items = deliveries.json().get("items") or []
    assert any(d.get("event") == "shoot_link.uploaded" and d.get("ok") for d in items)
