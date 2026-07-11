"""Аутентификация: регистрация, вход, JWT."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user
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
from app.services.legal import record_consents

router = APIRouter()


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
    }


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Вход, выдача JWT."""
    access, refresh = await auth_service.login_user(
        db, body.email, body.password, body.remember_me
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Обновление JWT по refresh-токену."""
    access, refresh = await auth_service.refresh_tokens(db, body.refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/logout")
async def logout(body: LogoutRequest, db: AsyncSession = Depends(get_db)):
    """Выход, отзыв refresh-токена."""
    await auth_service.logout_user(db, body.refresh_token)
    return {"message": "ok"}


@router.post("/password/reset")
@router.post("/password/forgot")
async def password_reset(body: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Запрос сброса пароля (в dev — токен в ответе)."""
    dev_token = await auth_service.request_password_reset(db, body.email)
    return {
        "message": "Если email зарегистрирован, инструкция отправлена",
        "dev_token": dev_token,
    }


@router.post("/password/confirm")
async def password_confirm(body: PasswordConfirmRequest, db: AsyncSession = Depends(get_db)):
    """Подтверждение сброса пароля."""
    await auth_service.confirm_password_reset(db, body.token, body.new_password)  # type: ignore[arg-type]
    return {"message": "Пароль обновлён"}
