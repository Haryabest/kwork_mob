"""Публичные .well-known для Universal/App Links (§3.15)."""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_public_apple_app_site_association(client):
    r = await client.get("/.well-known/apple-app-site-association")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/json")
    data = r.json()
    assert "applinks" in data
    assert "_meta" not in data
    details = data["applinks"]["details"]
    paths = {c["/"] for d in details for c in d.get("components", [])}
    assert "/shoot/*" in paths
    assert "/orders/*" in paths


async def test_public_android_assetlinks(client):
    r = await client.get("/.well-known/assetlinks.json")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["relation"] == ["delegate_permission/common.handle_all_urls"]
