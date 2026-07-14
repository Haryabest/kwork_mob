"""Thresholds for quality alerts §12.4.1."""

from app.services import quality_alerts as qa
from app.services import shoot_cleanup as sc


def test_quality_thresholds(monkeypatch):
    class S:
        PUBLICATION_CONVERSION_ALERT_RATIO = 0.30
        FALLBACK_SEGMENTATION_ALERT_RATIO = 0.15
        FALLBACK_SEGMENTATION_MIN_SAMPLES = 10
        SHOOT_LINK_PHOTO_TTL_DAYS = 7

    monkeypatch.setattr(qa, "settings", S())
    monkeypatch.setattr(sc, "settings", S())
    assert qa._pub_threshold() == 0.30
    assert qa._seg_threshold() == 0.15
    assert qa._seg_min_samples() == 10
    assert sc._photo_ttl_days() == 7


def test_applinks_team_placeholder(monkeypatch):
    from app.services import applinks as al

    class S:
        APPLE_TEAM_ID = ""
        IOS_BUNDLE_ID = "com.kwork.mob.kworkMobile"
        ANDROID_PACKAGE_NAME = "com.kwork.mob.kwork_mobile"
        ANDROID_SHA256_FINGERPRINTS = "AA:BB"
        SELLER_PUBLIC_URL = "https://3d.app"

    monkeypatch.setattr(al, "settings", S())
    aasa = al.apple_app_site_association()
    assert aasa["applinks"]["details"][0]["appIDs"] == ["TEAMID.com.kwork.mob.kworkMobile"]
    assert aasa["_meta"]["team_id_configured"] is False
    links = al.android_assetlinks()
    assert links[0]["target"]["sha256_cert_fingerprints"] == ["AA:BB"]
