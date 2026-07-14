"""Unit-тесты воронки публикации §7.9."""

from app.services.publication_funnel import _empty_funnel, _funnel_from_models, funnel_to_csv


def test_funnel_conversion():
    models = [type("M", (), {"uuid": "a", "publish_status": "verified_wb"})()]
    f = _funnel_from_models(
        models,
        downloaded={"a"},
        with_links={"a"},
        verified_links={"a": {"wb"}},
    )
    assert f["generated"] == 1
    assert f["verified"] == 1
    assert f["conversion"]["generated_to_verified"] == 1.0


def test_empty_funnel():
    f = _empty_funnel()
    assert f["generated"] == 0


def test_csv_export():
    body = funnel_to_csv({"funnel": _empty_funnel()})
    assert b"generated" in body
