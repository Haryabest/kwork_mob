"""Locale normalization §16."""

from app.services.locale import normalize_locale


def test_normalize_locale_defaults():
    assert normalize_locale(None) == "ru"
    assert normalize_locale("") == "ru"
    assert normalize_locale("bogus") == "ru"


def test_normalize_locale_supported():
    assert normalize_locale("en") == "en"
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("kk") == "kk"
    assert normalize_locale("zh") == "zh-CN"
    assert normalize_locale("zh-CN") == "zh-CN"


def test_normalize_locale_ru():
    assert normalize_locale("ru") == "ru"
    assert normalize_locale("RU") == "ru"
