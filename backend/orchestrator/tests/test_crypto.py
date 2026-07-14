"""Unit-тесты AES-256-GCM для ПД (§2.7)."""

import base64
import os

import pytest

from app.core import crypto
from app.core.config import settings


@pytest.fixture(autouse=True)
def _pd_key(monkeypatch):
    key = os.urandom(32)
    b64 = base64.urlsafe_b64encode(key).decode()
    monkeypatch.setattr(settings, "PD_ENCRYPTION_KEY", b64)
    monkeypatch.setattr(settings, "VAULT_ADDR", "")
    monkeypatch.setattr(settings, "VAULT_TOKEN", "")
    crypto.get_pd_encryption_key.cache_clear()
    yield
    crypto.get_pd_encryption_key.cache_clear()


def test_encrypt_decrypt_roundtrip():
    plain = "Иванов Иван, ул. Ленина 1"
    enc = crypto.encrypt_field(plain)
    assert enc and enc.startswith(crypto.ENC_PREFIX)
    assert crypto.decrypt_field(enc) == plain


def test_legacy_plaintext_passthrough():
    assert crypto.decrypt_field("legacy-name") == "legacy-name"


def test_idempotent_encrypt():
    enc = crypto.encrypt_field("secret")
    assert crypto.encrypt_field(enc) == enc
