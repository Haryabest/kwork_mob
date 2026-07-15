"""Unit tests for App Links payloads (no Postgres)."""

from app.services import applinks as al


def test_aasa_has_shoot_and_orders_paths():
    data = al.apple_app_site_association_public()
    paths = {
        c["/"]
        for d in data["applinks"]["details"]
        for c in d.get("components", [])
    }
    assert "/shoot/*" in paths
    assert "/orders/*" in paths
    assert "_meta" not in data


def test_assetlinks_structure():
    rows = al.android_assetlinks()
    assert len(rows) == 1
    assert rows[0]["target"]["namespace"] == "android_app"
    assert "sha256_cert_fingerprints" in rows[0]["target"]
