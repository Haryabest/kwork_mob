"""JWT-аутентификация и проверка прав."""

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, status
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


def _encode_token(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_access_token(user_id: int, role: str = UserRole.USER.value) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    return _encode_token(
        {
            "sub": str(user_id),
            "type": TokenType.ACCESS.value,
            "role": role,
            "exp": expire,
        }
    )


def create_refresh_token(
    user_id: int, jti: str | None = None, remember_me: bool = False
) -> tuple[str, str, datetime]:
    token_jti = jti or str(uuid.uuid4())
    days = settings.JWT_REFRESH_EXPIRE_DAYS if remember_me else min(settings.JWT_REFRESH_EXPIRE_DAYS, 7)
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    token = _encode_token(
        {
            "sub": str(user_id),
            "type": TokenType.REFRESH.value,
            "jti": token_jti,
            "exp": expires_at,
        }
    )
    return token, token_jti, expires_at


def decode_token(token: str, expected_type: TokenType | None = None) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный токен") from exc

    if expected_type and payload.get("type") != expected_type.value:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный тип токена")
    return payload


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    return decode_token(credentials.credentials, TokenType.ACCESS)


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
