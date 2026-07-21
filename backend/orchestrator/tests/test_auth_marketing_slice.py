"""§2.1 RS256 JWT, §2.3 single session, §2.5 marketing profile."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    TokenType,
    create_access_token,
    decode_token,
    jwt_uses_rs256,
)
from app.models import RefreshToken, User
from app.services import auth as auth_service
from app.services import marketing_profile as mp_svc
from app.services.campaigns import resolve_segment


def _rsa_keys() -> tuple[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def test_jwt_rs256_roundtrip(monkeypatch):
    private_pem, public_pem = _rsa_keys()
    monkeypatch.setattr(settings, "JWT_RSA_PRIVATE_KEY", private_pem)
    monkeypatch.setattr(settings, "JWT_RSA_PUBLIC_KEY", public_pem)
    assert jwt_uses_rs256() is True
    token = create_access_token(42, role="user")
    payload = decode_token(token, TokenType.ACCESS)
    assert payload["sub"] == "42"
    assert payload["role"] == "user"


def test_region_from_request_headers():
    class _Req:
        headers = {"X-Geo-Region": "Moscow"}

    assert mp_svc.region_from_request(_Req()) == "Moscow"


def test_card_issuer_from_payment():
    payment = {"payment_method": {"card": {"issuer_name": "Sberbank"}}}
    assert mp_svc.card_issuer_from_payment(payment) == "Sberbank"


@pytest.mark.asyncio
async def test_revoke_other_sessions_on_login(db, monkeypatch):
    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(auth_service, "_notify_other_sessions_revoked", _noop)
    user = User(
        email=f"session-{uuid.uuid4().hex[:8]}@test.local",
        password_hash="x",
        status="active_individual",
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    old_jti = str(uuid.uuid4())
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=old_jti,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
    )
    await db.commit()

    await auth_service.issue_tokens_for_user(db, user, remember_me=True)
    row = await db.scalar(select(RefreshToken).where(RefreshToken.jti == old_jti))
    assert row is not None
    assert row.revoked is True


@pytest.mark.asyncio
async def test_resolve_segment_gender_region(db):
    user = User(
        email=f"mkt-{uuid.uuid4().hex[:8]}@test.local",
        password_hash="x",
        status="active_individual",
        email_verified=True,
        gender="female",
        region="RU-MOW",
        card_bank_issuer="Tinkoff",
        marketing_opt_in=True,
    )
    db.add(user)
    await db.commit()

    matched = await resolve_segment(db, {"gender": "female", "region": "RU-MOW", "card_bank": "Tinkoff"})
    ids = {u.id for u in matched}
    assert user.id in ids

    empty = await resolve_segment(db, {"gender": "male", "region": "RU-MOW"})
    assert user.id not in {u.id for u in empty}
