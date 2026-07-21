"""§14.1 marketplace e2e, §14.2 ERP docs, §14.3 SMTP."""

from pathlib import Path

from app.services.email import smtp_health


def test_marketplace_e2e_ping_route():
    from app.api.v1 import marketplace_admin as mp

    paths = {getattr(r, "path", "") for r in mp.router.routes}
    assert any("e2e-ping" in p for p in paths)


def test_smtp_health_dev():
    out = smtp_health()
    assert "ok" in out


def test_erp_integration_doc():
    p = Path(__file__).resolve().parents[3] / "docs" / "b2b" / "README.md"
    text = p.read_text(encoding="utf-8")
    assert "ERP" in text or "1С" in text or "МойСклад" in text
