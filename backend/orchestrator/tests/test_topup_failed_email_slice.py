"""Topup failed email template §3.4.3."""

from app.services.email import _topup_failed_html, send_topup_failed_email


def test_topup_failed_html_contains_link():
    html = _topup_failed_html(
        title="Ошибка пополнения",
        body="Платёж не прошёл",
        balance_url="https://3d.app/balance",
    )
    assert "https://3d.app/balance" in html
    assert "Открыть баланс" in html
    assert "Ошибка пополнения" in html


def test_send_topup_failed_email_smoke():
    assert callable(send_topup_failed_email)
