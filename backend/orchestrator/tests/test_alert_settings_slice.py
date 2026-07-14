"""Tests: alert thresholds, shoot unblock, device UA, invoice PDF polish."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services import alert_thresholds as ath
from app.services import device_hint as dh
from app.services import shoot_link_limits as sll
from app.services import tax as tax_svc


def test_merge_thresholds_defaults():
    m = ath.merge_thresholds({})
    assert m["queue_alert_length"] == 20
    assert m["all_busy_alert_minutes"] == 5
    assert m["shoot_link_mass_limit_per_hour"] == 100


def test_merge_thresholds_patch():
    m = ath.merge_thresholds({"queue_alert_length": 50, "bogus": 1})
    assert m["queue_alert_length"] == 50
    assert "bogus" not in m


def test_device_hint_from_ua():
    d, o = dh.device_hint_from_ua(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
    )
    assert d == "Windows"
    assert o and "Windows" in o

    d2, _ = dh.device_hint_from_ua(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
    )
    assert d2 == "iOS Web"


def test_clear_block_if_expired():
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    company = SimpleNamespace(settings={"shoot_link_blocked_until": past, "shoot_link_block_reason": "mass"})
    assert sll.clear_block_if_expired(company) is True
    assert "shoot_link_blocked_until" not in company.settings
    assert company.settings.get("shoot_link_unblocked_at")


def test_active_block_not_cleared():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    company = SimpleNamespace(settings={"shoot_link_blocked_until": future})
    assert sll.clear_block_if_expired(company) is False
    assert sll.is_shoot_link_blocked(company) is not None


def test_invoice_pdf_bytes():
    tax = SimpleNamespace(
        mode="self_employed",
        vat_rate=0,
    )
    # pii tax_row_plain needs real-ish fields — stub via monkeypatch in call site
    order = SimpleNamespace(
        id=42,
        created_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        tier="small",
        amount=2990,
        amount_original=2990,
        upsell_amount=0,
        discount_amount=0,
        upsell_options=[],
        task_uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        customer_name=None,
    )

    class FakePii:
        @staticmethod
        def tax_row_plain(_tax):
            return {
                "full_name": "Иванов И.И.",
                "inn": "123456789012",
                "ogrnip": "",
                "ogrn": "",
                "kpp": "",
                "org_name": "",
                "legal_address": "г. Москва",
                "bank_account": "",
                "bank_bik": "",
                "bank_name": "",
            }

    import app.services.tax as tax_mod

    orig = tax_mod.pii_svc
    tax_mod.pii_svc = FakePii
    try:
        pdf = tax_svc.build_invoice_pdf(
            tax=tax,
            order=order,
            buyer_email="buyer@example.com",
            doc_type="invoice",
            buyer_name="ООО Покупатель",
            buyer_inn="7701234567",
        )
    finally:
        tax_mod.pii_svc = orig
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500
