"""§2.2 DaData, §2.6 remember me TTL, §2.7 PII Vault."""

from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.core import crypto
from app.core.config import settings
from app.core.security import create_refresh_token, refresh_token_expire_days
from app.models import RefreshToken, User
from app.services import auth as auth_service
from app.services import dadata as dadata_svc


def test_refresh_token_expire_days_remember():
    assert refresh_token_expire_days(True) == settings.JWT_REFRESH_EXPIRE_DAYS


def test_refresh_token_expire_days_session():
    assert refresh_token_expire_days(False) == settings.JWT_REFRESH_SESSION_DAYS


def test_create_refresh_token_includes_remember_flag():
    _, _, exp = create_refresh_token(1, remember_me=True)
    assert exp > datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS - 1)


@pytest.mark.asyncio
async def test_refresh_preserves_remember_me(db):
    user = User(
        email=f"rem-{uuid.uuid4().hex[:8]}@test.local",
        password_hash="x",
        status="active_individual",
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    _, jti, expires = create_refresh_token(user.id, remember_me=True)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires, remember_me=True))
    await db.commit()

    from app.core.security import _encode_token

    refresh = _encode_token(
        {
            "sub": str(user.id),
            "type": "refresh",
            "jti": jti,
            "remember": True,
            "exp": expires,
        }
    )
    access, new_refresh = await auth_service.refresh_tokens(db, refresh)
    assert access
    assert new_refresh
    row = await db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    assert row and row.revoked is True
    new_row = (
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
            )
        )
    ).first()
    assert new_row is not None
    assert new_row.remember_me is True


@pytest.mark.asyncio
async def test_dadata_dev_lookup():
    result = await dadata_svc.lookup_inn("7707083893")
    assert result.found is True
    assert result.inn == "7707083893"


@pytest.mark.asyncio
async def test_dadata_verify_mismatch():
    lookup = await dadata_svc.lookup_inn("7707083893")
    verify = await dadata_svc.verify_legal_entity(
        inn="7707083893",
        company_name="Wrong Name LLC",
        kpp=lookup.kpp,
        ogrn=lookup.ogrn,
        legal_address=lookup.legal_address,
    )
    assert verify.verified is False
    assert verify.mismatches


def test_company_verification_allowed():
    assert dadata_svc.company_verification_allowed({"verification": {"status": "dadata_verified"}})
    assert not dadata_svc.company_verification_allowed({"verification": {"status": "pending"}})


def test_pii_encryption_status_env(monkeypatch):
    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    monkeypatch.setattr(settings, "PD_ENCRYPTION_KEY", key)
    monkeypatch.setattr(settings, "VAULT_ADDR", "")
    crypto.get_pd_encryption_key.cache_clear()
    status = crypto.pii_encryption_status()
    assert status["ok"] is True
    assert status["source"] == "env"
    crypto.get_pd_encryption_key.cache_clear()


def test_pii_vault_key_load(monkeypatch):
    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    monkeypatch.setattr(settings, "PD_ENCRYPTION_KEY", "")
    monkeypatch.setattr(settings, "VAULT_ADDR", "http://vault:8200")
    monkeypatch.setattr(settings, "VAULT_TOKEN", "test-token")
    crypto.get_pd_encryption_key.cache_clear()

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": {"data": {"key": key}}}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.core.crypto.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        loaded = crypto.get_pd_encryption_key()
    assert len(loaded) == 32
    crypto.get_pd_encryption_key.cache_clear()
