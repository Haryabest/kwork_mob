"""JWT-аутентификация и проверка прав."""

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    USER = "user"
    OWNER = "owner"
    MANAGER = "manager"
    PHOTOGRAPHER = "photographer"
    VIEWER = "viewer"
    ADMIN = "admin"
    SUPPORT_AGENT = "support_agent"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _normalize_pem(pem: str) -> str:
    if not pem:
        return ""
    return pem.replace("\\n", "\n").strip()


def jwt_uses_rs256() -> bool:
    return bool(_normalize_pem(settings.JWT_RSA_PRIVATE_KEY) and _normalize_pem(settings.JWT_RSA_PUBLIC_KEY))


def _signing_key() -> tuple[str, str]:
    if jwt_uses_rs256():
        return _normalize_pem(settings.JWT_RSA_PRIVATE_KEY), "RS256"
    return settings.JWT_SECRET, "HS256"


def _decode_algorithms() -> list[str]:
    if jwt_uses_rs256():
        if settings.is_development:
            return ["RS256", "HS256"]
        return ["RS256"]
    return ["HS256"]


def _verification_key_for_alg(alg: str) -> str:
    if alg == "RS256":
        return _normalize_pem(settings.JWT_RSA_PUBLIC_KEY)
    return settings.JWT_SECRET


def _encode_token(payload: dict[str, Any]) -> str:
    key, alg = _signing_key()
    return jwt.encode(payload, key, algorithm=alg)


def create_access_token(
    user_id: int,
    role: str = UserRole.USER.value,
    *,
    extra: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": TokenType.ACCESS.value,
        "role": role,
        "exp": expire,
    }
    if extra:
        payload.update(extra)
    return _encode_token(payload)


def refresh_token_expire_days(remember_me: bool) -> int:
    """TTL refresh-токена: 30 дней с «Запомнить меня», иначе сессия (§2.3)."""
    if remember_me:
        return settings.JWT_REFRESH_EXPIRE_DAYS
    return settings.JWT_REFRESH_SESSION_DAYS


def create_refresh_token(
    user_id: int, jti: str | None = None, remember_me: bool = False
) -> tuple[str, str, datetime]:
    token_jti = jti or str(uuid.uuid4())
    days = refresh_token_expire_days(remember_me)
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    token = _encode_token(
        {
            "sub": str(user_id),
            "type": TokenType.REFRESH.value,
            "jti": token_jti,
            "remember": remember_me,
            "exp": expires_at,
        }
    )
    return token, token_jti, expires_at


def decode_token(token: str, expected_type: TokenType | None = None) -> dict:
    last_exc: JWTError | None = None
    payload: dict[str, Any] | None = None
    for alg in _decode_algorithms():
        try:
            payload = jwt.decode(token, _verification_key_for_alg(alg), algorithms=[alg])
            break
        except JWTError as exc:
            last_exc = exc
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный токен") from last_exc

    if expected_type and payload.get("type") != expected_type.value:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный тип токена")
    return payload


async def get_access_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.services.auth_cookies import ACCESS_COOKIE

    cookie_token = request.cookies.get(ACCESS_COOKIE)
    if cookie_token:
        return cookie_token
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Не авторизован")


async def get_current_user(
    token: Annotated[str, Depends(get_access_token)],
) -> dict:
    return decode_token(token, TokenType.ACCESS)


async def get_current_db_user(
    token_data: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.models import User

    user = await db.get(User, int(token_data["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    if user.status in ("blocked", "blocked_pending_review", "blocked_permanent"):
        detail = (
            "Аккаунт на проверке модерации (NSFW)"
            if user.status == "blocked_pending_review"
            else "Аккаунт заблокирован"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail)
    return user


async def get_current_db_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not credentials:
        return None
    token_data = decode_token(credentials.credentials, TokenType.ACCESS)
    from app.models import User

    user = await db.get(User, int(token_data["sub"]))
    if not user:
        return None
    if user.status in ("blocked", "blocked_pending_review", "blocked_permanent"):
        return None
    return user


async def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if user.get("role") not in (UserRole.ADMIN.value,):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Требуются права администратора")
    return user


async def require_staff(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if user.get("role") not in (UserRole.ADMIN.value, UserRole.SUPPORT_AGENT.value):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Требуются права сотрудника")
    return user


def jwt_gateway_status() -> dict[str, Any]:
    """Статус JWT gateway для /health (§4.1.3 / §4.3)."""
    rs256 = jwt_uses_rs256()
    return {
        "algorithm": "RS256" if rs256 else "HS256",
        "rs256_configured": rs256,
        "production_ready": rs256 or settings.is_development,
    }


def ensure_jwt_gateway_ready() -> None:
    """Prod: RS256 обязателен на API Gateway (§4.1.3)."""
    if settings.is_development:
        return
    if not jwt_uses_rs256():
        raise RuntimeError(
            "Production API Gateway requires JWT_RSA_PRIVATE_KEY and JWT_RSA_PUBLIC_KEY (RS256 §4.1.3)"
        )


def jwt_public_jwks() -> dict[str, Any]:
    """Публичный ключ для верификации JWT (gateway / внешние сервисы)."""
    if not jwt_uses_rs256():
        return {"keys": []}
    pem = _normalize_pem(settings.JWT_RSA_PUBLIC_KEY)
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "kwork-mob-1",
                "pem": pem,
            }
        ]
    }
