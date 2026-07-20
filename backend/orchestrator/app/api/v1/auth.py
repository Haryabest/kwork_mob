"""Аутентификация: регистрация, вход, JWT, 2FA Owner (§10)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    TokenType,
    decode_token,
    get_current_db_user,
    verify_password,
)
from app.core.vpn import client_ip
from app.models import RefreshToken, User
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
from app.schemas.oauth import (
    OAuthCallbackBody,
    OAuthProvidersResponse,
    OAuthStartResponse,
    OAuthTokenResponse,
)
from app.services import oauth_auth as oauth_svc
from app.services import oauth_providers as oauth_providers_svc
from app.services.company_owner_2fa import user_is_company_owner
from app.services.legal import record_consents

router = APIRouter()


@router.get("/oauth/providers", response_model=OAuthProvidersResponse)
async def oauth_providers():
    """Доступные OAuth-провайдеры (VK / Yandex / Sber)."""
    return OAuthProvidersResponse(items=oauth_providers_svc.list_enabled_providers())


@router.get("/oauth/{provider}/authorize", response_model=OAuthStartResponse)
async def oauth_authorize(
    provider: str,
    request: Request,
    redirect_uri: str | None = None,
    platform: str = "web",
    mode: str = "login",
    consents: str | None = None,
):
    """Старт OAuth — URL для редиректа на провайдера."""
    consent_list = [c.strip() for c in consents.split(",")] if consents else None
    data = await oauth_svc.start_oauth(
        provider,
        redirect_uri=redirect_uri,
        platform=platform,
        mode=mode,
        consents=consent_list,
    )
    return OAuthStartResponse(**data)


@router.post("/oauth/{provider}/callback", response_model=OAuthTokenResponse)
async def oauth_callback(
    provider: str,
    body: OAuthCallbackBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Обмен code→токены после редиректа с провайдера."""
    user, access, refresh = await oauth_svc.complete_oauth(
        db,
        provider,
        code=body.code,
        state=body.state,
        redirect_uri=body.redirect_uri,
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    is_owner = await user_is_company_owner(db, user)
    return OAuthTokenResponse(
        access_token=access,
        refresh_token=refresh,
        status=user.status,
        owner_2fa_required=is_owner and not user.totp_enabled,
    )


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
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
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
    if not verify_password(body.old_password, user.password_hash or ""):
        raise HTTPException(400, "Неверный текущий пароль")
    auth_service.validate_password_strength(body.new_password)
    from app.core.security import hash_password

    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}


@router.post("/2fa/disable")
async def two_fa_disable(
    body: TwoFACodeBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Отключение TOTP (§20.8). Для Owner компании 2FA обязательна — запрещаем."""
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(400, "2FA не включена")
    if await user_is_company_owner(db, user):
        raise HTTPException(403, "Для владельца компании 2FA обязательна")
    if not totp_svc.verify_totp(user.totp_secret, body.code):
        raise HTTPException(400, "Неверный код подтверждения")
    user.totp_enabled = False
    user.totp_secret = None
    await db.commit()
    return {"ok": True, "totp_enabled": False}


@router.get("/sessions")
async def list_sessions(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Активные сессии (refresh-токены) пользователя (§20.8)."""
    now = datetime.now(timezone.utc)
    rows = (
        await db.scalars(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > now,
            )
            .order_by(RefreshToken.created_at.desc())
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in rows
        ]
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Завершить конкретную сессию пользователя (§20.8)."""
    row = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.id == session_id, RefreshToken.user_id == user.id
        )
    )
    if not row:
        raise HTTPException(404, "Сессия не найдена")
    row.revoked = True
    await db.commit()
    return {"ok": True}


class RevokeOthersBody(BaseModel):
    refresh_token: str


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(
    body: RevokeOthersBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Завершить все сессии, кроме текущей (§20.8)."""
    try:
        payload = decode_token(body.refresh_token, TokenType.REFRESH)
        current_jti = payload.get("jti")
    except Exception:
        raise HTTPException(400, "Неверный refresh-токен")
    rows = (
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
                RefreshToken.jti != current_jti,
            )
        )
    ).all()
    for r in rows:
        r.revoked = True
    await db.commit()
    return {"ok": True, "revoked": len(rows)}