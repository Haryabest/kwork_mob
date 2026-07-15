"""Индивидуальные цены B2B §11.4."""

from app.services.tariffs import apply_company_override


def test_no_override_returns_base():
    assert apply_company_override(2990, None) == 2990
    assert apply_company_override(2990, {}) == 2990


def test_fixed_override():
    assert apply_company_override(2990, {"type": "fixed", "value": 2500}) == 2500
    assert apply_company_override(2990, {"type": "fixed", "value": 0}) == 0


def test_percent_override():
    assert apply_company_override(1000, {"type": "percent", "value": 10}) == 900
    assert apply_company_override(1000, {"type": "percent", "value": 100}) == 0


def test_invalid_override_ignored():
    assert apply_company_override(2990, {"type": "percent", "value": 150}) == 2990
    assert apply_company_override(2990, {"type": "bogus", "value": 10}) == 2990
    assert apply_company_override(2990, {"type": "fixed", "value": "x"}) == 2990
