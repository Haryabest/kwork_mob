"""Email templates §16.2.2."""

from app.services import email_templates as tpl


def test_verification_ru():
    subj, body = tpl.verification_email("ru", code="123456")
    assert "123456" in body
    assert "код" in subj.lower() or "3dvektor" in subj.lower()


def test_verification_en():
    subj, body = tpl.verification_email("en", code="999999")
    assert "999999" in body
    assert "verification" in subj.lower() or "3dvektor" in subj.lower()


def test_password_reset_fallback_ru():
    subj, body = tpl.password_reset_email("xx", reset_token="tok")
    assert "reset-password" in body
    assert subj


def test_topup_failed_locales():
    subj, body, cta, loc = tpl.topup_failed_email(
        "zh-CN", title="T", body="B", balance_url="https://x/balance"
    )
    assert loc == "zh-CN"
    assert "https://x/balance" in body
    assert cta
