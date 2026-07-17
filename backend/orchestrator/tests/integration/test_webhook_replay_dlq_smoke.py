"""Webhook DLQ replay integration smoke §14.5.4."""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


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


async def test_webhook_replay_dlq(client, unique_email, db, monkeypatch):
    headers = await _login_owner(client, unique_email)

    wh = await client.post(
        "/api/v1/company/webhooks",
        headers=headers,
        json={
            "url": "https://hooks.example/dlq-replay",
            "events": ["shoot_link.uploaded"],
            "secret": "dlq-test",
        },
    )
    assert wh.status_code == 200
    webhook_id = wh.json()["id"]

    from app.models import CompanyWebhookDelivery

    delivery = CompanyWebhookDelivery(
        webhook_id=webhook_id,
        event="shoot_link.uploaded",
        payload={
            "event": "shoot_link.uploaded",
            "company_id": 1,
            "data": {"token": "dlq-test-token"},
        },
        ok=False,
        status="dlq",
        attempt=10,
        max_attempts=10,
        error="simulated failure",
    )
    db.add(delivery)
    await db.flush()
    delivery_id = delivery.id
    await db.commit()

    async def _fake_deliver(hook, d):
        d.ok = True
        d.status_code = 200
        return True

    monkeypatch.setattr("app.services.company_webhooks._deliver_once", _fake_deliver)

    replay = await client.post("/api/v1/company/webhooks/deliveries/replay-dlq", headers=headers)
    assert replay.status_code == 200
    body = replay.json()
    assert body.get("replayed", 0) >= 1
    assert body.get("delivered", 0) >= 1

    deliveries = await client.get(
        "/api/v1/company/webhooks/deliveries",
        headers=headers,
        params={"status": "delivered"},
    )
    assert deliveries.status_code == 200
    items = deliveries.json().get("items") or []
    assert any(d.get("id") == delivery_id and d.get("status") == "delivered" for d in items)
