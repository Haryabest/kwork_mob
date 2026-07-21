"""§4.3 JWT RS256 gateway, §4.4 cloud owner loop, §4.5 rate limit."""

from __future__ import annotations

import inspect

import pytest
from starlette.requests import Request

from app.core.config import settings
from app.core.security import (
    TokenType,
    create_access_token,
    decode_token,
    ensure_jwt_gateway_ready,
    jwt_gateway_status,
    jwt_public_jwks,
)
from app.services import gateway_rate_limit as gw_rl


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


def test_jwt_gateway_status_rs256(monkeypatch):
    private_pem, public_pem = _rsa_keys()
    monkeypatch.setattr(settings, "JWT_RSA_PRIVATE_KEY", private_pem)
    monkeypatch.setattr(settings, "JWT_RSA_PUBLIC_KEY", public_pem)
    st = jwt_gateway_status()
    assert st["rs256_configured"] is True
    assert st["algorithm"] == "RS256"
    jwks = jwt_public_jwks()
    assert len(jwks["keys"]) == 1
    assert jwks["keys"][0]["alg"] == "RS256"


def test_ensure_jwt_gateway_prod_requires_rs256(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "JWT_RSA_PRIVATE_KEY", "")
    monkeypatch.setattr(settings, "JWT_RSA_PUBLIC_KEY", "")
    with pytest.raises(RuntimeError, match="RS256"):
        ensure_jwt_gateway_ready()


def test_prod_rejects_hs256_token(monkeypatch):
    private_pem, public_pem = _rsa_keys()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "JWT_RSA_PRIVATE_KEY", private_pem)
    monkeypatch.setattr(settings, "JWT_RSA_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(settings, "JWT_SECRET", "dev-only")
    from jose import jwt as jose_jwt

    hs_token = jose_jwt.encode(
        {"sub": "1", "type": TokenType.ACCESS.value, "role": "user", "exp": 9999999999},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(Exception):  # HTTPException 401
        decode_token(hs_token, TokenType.ACCESS)
    rs_token = create_access_token(1)
    assert decode_token(rs_token, TokenType.ACCESS)["sub"] == "1"


def test_client_ip_x_forwarded_for():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", b"203.0.113.1, 10.0.0.1")],
        "client": ("10.0.0.2", 1234),
    }
    req = Request(scope)
    assert gw_rl.client_ip(req) == "203.0.113.1"


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_threshold(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_DISABLED", raising=False)
    class FakeRedis:
        def __init__(self):
            self.data: dict[str, int] = {}

        async def get(self, key):
            return self.data.get(key)

        async def incr(self, key):
            self.data[key] = self.data.get(key, 0) + 1
            return self.data[key]

        async def expire(self, key, _sec):
            return True

        async def setex(self, key, _sec, val):
            self.data[key] = val

    redis = FakeRedis()

    async def fake_limits():
        return {
            "gateway_ip_rate_limit_per_min": 2,
            "gateway_jwt_rate_limit_per_min": 2,
            "gateway_rate_block_sec": 60,
        }

    monkeypatch.setattr(gw_rl, "load_limits", fake_limits)
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "client": ("1.2.3.4", 80)}
    req = Request(scope)
    ok1, _, _ = await gw_rl.check_request(req, redis)
    ok2, _, _ = await gw_rl.check_request(req, redis)
    ok3, retry, _ = await gw_rl.check_request(req, redis)
    assert ok1 and ok2
    assert not ok3
    assert retry == 60


def test_cloud_admin_endpoints_exist():
    from app.api.v1 import cloud_admin as ca

    paths = {getattr(r, "path", "") for r in ca.router.routes}
    assert "/cloud/autoscaling/status" in paths
    assert "/cloud/autoscaling/approve" in paths
    assert "/cloud/instances/{instance_id}/terminate" in paths


def test_run_autoscaling_signature():
    from app.services import cloud_autoscaling as cas

    sig = inspect.signature(cas.run_autoscaling_once)
    assert "db" in sig.parameters
