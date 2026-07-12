"""NSFW policy unit tests (без MinIO)."""

from app.services.nsfw import NsfwService


def test_blacklist_hit():
    svc = NsfwService()
    assert svc.check_blacklist("weapon xxx porn") is True  # via DEFAULT_BLACKLIST latin
    assert svc.check_blacklist("\u043e\u0440\u0443\u0436\u0438\u0435") is True  # оружие
    assert svc.check_blacklist("wooden chair") is False


def test_aggregate_nsfw():
    svc = NsfwService()
    out = svc._aggregate(
        [
            {"name": "a", "is_nsfw": False, "confidence": 0.1, "method": "x"},
            {"name": "b", "is_nsfw": True, "confidence": 0.9, "method": "y"},
        ]
    )
    assert out["is_nsfw"] is True
    assert out["confidence"] == 0.9
    assert out["trigger"] == "b"


def test_marker_in_bytes(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "NSFW_FORCE_BLOCK", False)
    monkeypatch.setattr(config.settings, "NSFW_THRESHOLD", 0.85)
    monkeypatch.setattr(config.settings, "NSFW_MODE", "heuristic")
    svc = NsfwService()
    data = b"\xff\xd8\xffNSFW_TEST_BLOCK" + b"\x00" * 100
    r = svc._analyze_image("view_00.jpg", data)
    assert r["is_nsfw"] is True
    assert r["method"] == "marker"
