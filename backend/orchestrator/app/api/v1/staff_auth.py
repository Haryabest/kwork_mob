"""Staff login: VPN + пароль + TOTP 2FA (§11)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    UserRole,
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.core.vpn import is_vpn_ip, require_vpn
from app.models import RefreshToken, User
from app.schemas.auth import TokenResponse
from app.services.totp import (
    CHALLENGE_TYPE_SETUP,
    CHALLENGE_TYPE_VERIFY,
    create_challenge_token,
    decode_challenge_token,
    generate_totp_secret,
    qr_data_url,
    totp_uri,
    verify_totp,
)

router = APIRouter(prefix="/staff", tags=["Staff auth (VPN+2FA)"])


class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str


class StaffTotpConfirm(BaseModel):
    challenge_token: str
    code: str = Field(min_length=6, max_length=8)


class StaffTotpSetupStart(BaseModel):
    challenge_token: str


async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    from app.services import auth as auth_service

    await auth_service.revoke_other_refresh_sessions(db, user.id)
    access = create_access_token(user.id, role=user.staff_role or "", extra={"staff": True})
    refresh, jti, expires_at = create_refresh_token(user.id, remember_me=True)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/vpn-status")
async def vpn_status(request: Request):
    """Проверка, видит ли API клиента как VPN."""
    from app.core.vpn import client_ip

    ip = client_ip(request)
    return {
        "ip": ip,
        "vpn_required": settings.ADMIN_VPN_REQUIRED,
        "vpn_ok": is_vpn_ip(ip) if settings.ADMIN_VPN_REQUIRED else True,
        "allowed_cidrs": settings.vpn_cidrs if settings.ADMIN_VPN_REQUIRED else [],
        "two_fa_required": settings.ADMIN_2FA_REQUIRED,
        "idle_timeout_minutes": settings.STAFF_IDLE_TIMEOUT_MINUTES,
    }


@router.post("/login")
async def staff_login(body: StaffLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Шаг 1: пароль + VPN. Далее setup или verify TOTP."""
    require_vpn(request)

    email = body.email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not user.staff_role or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    if user.staff_role not in (UserRole.ADMIN.value, UserRole.SUPPORT_AGENT.value):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет прав сотрудника")
    if user.status == "blocked":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Аккаунт заблокирован")

    if settings.ADMIN_2FA_REQUIRED and not user.totp_enabled:
        challenge = create_challenge_token(user.id, CHALLENGE_TYPE_SETUP)
        return {
            "status": "setup_2fa",
            "challenge_token": challenge,
            "message": "Настройте 2FA (TOTP) — обязательно для Staff Panel",
        }

    if user.totp_enabled or settings.ADMIN_2FA_REQUIRED:
        challenge = create_challenge_token(user.id, CHALLENGE_TYPE_VERIFY)
        return {
            "status": "need_2fa",
            "challenge_token": challenge,
            "message": "Введите код из приложения-аутентификатора",
        }

    tokens = await _issue_tokens(db, user)
    await db.commit()
    return {"status": "ok", **tokens.model_dump()}


@router.post("/2fa/setup")
async def staff_2fa_setup(body: StaffTotpSetupStart, request: Request, db: AsyncSession = Depends(get_db)):
    """Генерация секрета + QR для привязки Authenticator."""
    require_vpn(request)
    payload = decode_challenge_token(body.challenge_token, CHALLENGE_TYPE_SETUP)
    user = await db.get(User, int(payload["sub"]))
    if not user or not user.staff_role:
        raise HTTPException(404, "Пользователь не найден")

    secret = generate_totp_secret()
    user.totp_secret = secret
    user.totp_enabled = False
    await db.commit()

    challenge = create_challenge_token(user.id, CHALLENGE_TYPE_SETUP)
    uri = totp_uri(secret, user.email)
    return {
        "challenge_token": challenge,
        "secret": secret,
        "otpauth_uri": uri,
        "qr_data_url": qr_data_url(uri),
        "message": "Отсканируйте QR в Google Authenticator / Authy и подтвердите кодом",
    }


@router.post("/2fa/confirm", response_model=TokenResponse)
async def staff_2fa_confirm(body: StaffTotpConfirm, request: Request, db: AsyncSession = Depends(get_db)):
    """Подтверждение привязки 2FA → выдача JWT."""
    require_vpn(request)
    payload = decode_challenge_token(body.challenge_token, CHALLENGE_TYPE_SETUP)
    user = await db.get(User, int(payload["sub"]))
    if not user or not user.totp_secret:
        raise HTTPException(400, "Сначала запросите setup 2FA")
    if not verify_totp(user.totp_secret, body.code):
        raise HTTPException(400, "Неверный код 2FA")

    user.totp_enabled = True
    tokens = await _issue_tokens(db, user)
    await db.commit()
    return tokens


@router.post("/2fa/verify", response_model=TokenResponse)
async def staff_2fa_verify(body: StaffTotpConfirm, request: Request, db: AsyncSession = Depends(get_db)):
    """Проверка TOTP при каждом входе."""
    require_vpn(request)
    payload = decode_challenge_token(body.challenge_token, CHALLENGE_TYPE_VERIFY)
    user = await db.get(User, int(payload["sub"]))
    if not user or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(400, "2FA не настроена")
    if not verify_totp(user.totp_secret, body.code):
        raise HTTPException(401, "Неверный код 2FA")

    tokens = await _issue_tokens(db, user)
    await db.commit()
    return tokens
