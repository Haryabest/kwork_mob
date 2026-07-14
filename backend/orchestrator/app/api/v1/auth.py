"""Аутентификация: регистрация, вход, JWT, 2FA Owner (§10)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user, verify_password
from app.core.vpn import client_ip
from app.models import User
from app.schemas.auth import (
    AccountTypeRequest,
    LoginRequest,
    LogoutRequest,
    PasswordConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services import auth as auth_service
from app.services import totp as totp_svc
from app.services.company_owner_2fa import user_is_company_owner
from app.services.legal import record_consents

router = APIRouter()


class TwoFACodeBody(BaseModel):
    code: str = Field(min_length=6, max_length=8)
    challenge_token: str | None = None
    remember_me: bool = False


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Регистрация по email + пароль + согласия (§2.8)."""
    user, dev_code = await auth_service.register_user(db, body.email, body.password)
    await record_consents(
        db,
        user.id,
        body.consents,
        client_ip(request),
        request.headers.get("user-agent"),
    )
    await db.commit()
    return RegisterResponse(
        message="Код подтверждения отправлен на email",
        email=user.email,
        dev_code=dev_code,
    )


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Подтверждение email → JWT для выбора типа аккаунта."""
    user = await auth_service.verify_email(db, body.email, body.code)
    access, refresh = await auth_service.issue_tokens_for_user(db, user, remember_me=True)
    return VerifyEmailResponse(
        message="Email подтверждён. Выберите тип аккаунта.",
        status=user.status,
        access_token=access,
        refresh_token=refresh,
    )


@router.post("/account-type")
async def account_type(
    body: AccountTypeRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Выбор типа аккаунта: individual | legal (+ реквизиты юрлица)."""
    updated = await auth_service.set_account_type(db, user, body)
    return {
        "message": "Тип аккаунта сохранён",
        "status": updated.status,
        "account_type": updated.account_type,
        "owner_2fa_required": updated.account_type == "legal" and not updated.totp_enabled,
    }


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Вход. Owner с 2FA → challenge; иначе JWT."""
    email = body.email.lower().strip()
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    if not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Подтвердите email перед входом")
    if user.status in ("blocked", "deleted"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Аккаунт недоступен")

    if user.totp_enabled and user.totp_secret:
        challenge = totp_svc.create_challenge_token(
            user.id,
            totp_svc.CHALLENGE_LOGIN_2FA,
            extra={"remember_me": body.remember_me},
        )
        return {
            "requires_2fa": True,
            "challenge_token": challenge,
            "message": "Введите код из приложения-аутентификатора",
        }

    access, refresh = await auth_service.issue_tokens_for_user(db, user, remember_me=body.remember_me)
    is_owner = await user_is_company_owner(db, user)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "requires_2fa": False,
        "owner_2fa_required": is_owner and not user.totp_enabled,
    }


@router.post("/2fa/verify-login", response_model=TokenResponse)
async def verify_login_2fa(body: TwoFACodeBody, db: AsyncSession = Depends(get_db)):
    if not body.challenge_token:
        raise HTTPException(400, "challenge_token обязателен")
    payload = totp_svc.decode_challenge_token(body.challenge_token, totp_svc.CHALLENGE_LOGIN_2FA)
    user = await db.get(User, int(payload["sub"]))
    if not user or not user.totp_secret or not totp_svc.verify_totp(user.totp_secret, body.code):
        raise HTTPException(401, "Неверный код 2FA")
    remember = bool(payload.get("remember_me"))
    access, refresh = await auth_service.issue_tokens_for_user(db, user, remember_me=remember)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/2fa/setup")
async def owner_2fa_setup(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Настройка TOTP для Owner / любого пользователя (§10)."""
    if user.totp_enabled:
        raise HTTPException(400, "2FA уже включена")
    secret = totp_svc.generate_totp_secret()
    user.totp_secret = secret
    await db.commit()
    uri = totp_svc.totp_uri(secret, user.email, issuer="KWork Mob")
    challenge = totp_svc.create_challenge_token(user.id, totp_svc.CHALLENGE_OWNER_SETUP)
    return {
        "secret": secret,
        "otpauth_uri": uri,
        "qr_data_url": totp_svc.qr_data_url(uri),
        "challenge_token": challenge,
    }


@router.post("/2fa/confirm")
async def owner_2fa_confirm(
    body: TwoFACodeBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.totp_secret:
        raise HTTPException(400, "Сначала вызовите /auth/2fa/setup")
    if body.challenge_token:
        totp_svc.decode_challenge_token(body.challenge_token, totp_svc.CHALLENGE_OWNER_SETUP)
    if not totp_svc.verify_totp(user.totp_secret, body.code):
        raise HTTPException(400, "Неверный код подтверждения")
    user.totp_enabled = True
    await db.commit()
    return {"ok": True, "totp_enabled": True}


@router.get("/2fa/status")
async def owner_2fa_status(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    is_owner = await user_is_company_owner(db, user)
    return {
        "totp_enabled": bool(user.totp_enabled),
        "is_company_owner": is_owner,
        "owner_2fa_required": is_owner and not user.totp_enabled,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    access, refresh = await auth_service.refresh_tokens(db, body.refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/logout")
async def logout(body: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.logout_user(db, body.refresh_token)
    return {"message": "ok"}


@router.post("/password/reset")
@router.post("/password/forgot")
async def password_reset(body: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    dev_token = await auth_service.request_password_reset(db, body.email)
    return {
        "message": "Если email зарегистрирован, инструкция отправлена",
        "dev_token": dev_token,
    }


@router.post("/password/confirm")
async def password_confirm(body: PasswordConfirmRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.confirm_password_reset(db, body.token, body.new_password)  # type: ignore[arg-type]
    return {"message": "Пароль обновлён"}


class PasswordChangeBody(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


@router.post("/password/change")
async def password_change(
    body: PasswordChangeBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Смена пароля в настройках (§20.8.2)."""
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "Неверный текущий пароль")
    auth_service.validate_password_strength(body.new_password)
    from app.core.security import hash_password

    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}