"""Universal Links / App Links payloads из env (§3.15)."""

from __future__ import annotations

from typing import Any

from app.core.config import settings


def apple_app_site_association() -> dict[str, Any]:
    team = (settings.APPLE_TEAM_ID or "").strip() or "TEAMID"
    bundle = (settings.IOS_BUNDLE_ID or "com.kwork.mob.kworkMobile").strip()
    app_id = f"{team}.{bundle}"
    return {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appIDs": [app_id],
                    "components": [
                        {
                            "/": "/shoot/*",
                            "comment": "§3.15 shoot-link Universal Links",
                        }
                    ],
                }
            ],
        },
        "_meta": {
            "seller_public_url": settings.SELLER_PUBLIC_URL,
            "team_id_configured": bool((settings.APPLE_TEAM_ID or "").strip()),
        },
    }


def android_assetlinks() -> list[dict[str, Any]]:
    fingerprints = [
        f.strip()
        for f in (settings.ANDROID_SHA256_FINGERPRINTS or "").split(",")
        if f.strip()
    ]
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": settings.ANDROID_PACKAGE_NAME or "com.kwork.mob.kwork_mobile",
                "sha256_cert_fingerprints": fingerprints,
            },
        }
    ]
