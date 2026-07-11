"""TOTP 2FA для staff (§11)."""

import io
import base64
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
from jose import jwt
from fastapi import HTTPException, status

from app.core.config import settings

CHALLENGE_TYPE_SETUP = "staff_2fa_setup"
CHALLENGE_TYPE_VERIFY = "staff_2fa_verify"


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="KWork Staff")


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def qr_data_url(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def create_challenge_token(user_id: int, challenge_type: str, extra: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {
        "sub": str(user_id),
        "type": challenge_type,
        "exp": expire,
        **(extra or {}),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_challenge_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный challenge-токен") from exc
    if payload.get("type") != expected_type:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный тип challenge-токена")
    return payload
