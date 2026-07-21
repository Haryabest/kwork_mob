"""Бизнес-логика аутентификации."""

import re
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import (
    TokenType,
    UserRole,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Company, CompanyMember, RefreshToken, User
from app.schemas.auth import AccountTypeRequest
from app.services import pii as pii_svc
from app.services.email import send_password_reset_email, send_verification_email

EMAIL_CODE_PREFIX = "email_verify:"
PASSWORD_RESET_PREFIX = "password_reset:"

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).+$")


def validate_password_strength(password: str) -> None:
    if not PASSWORD_PATTERN.match(password):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Пароль должен содержать буквы и цифры",
        )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _store_email_code(email: str, code: str) -> None:
    from app.core.config import settings

    redis = await get_redis()
    await redis.set(f"{EMAIL_CODE_PREFIX}{email}", code, ex=settings.EMAIL_VERIFY_CODE_TTL_SECONDS)


async def _get_email_code(email: str) -> str | None:
    redis = await get_redis()
    return await redis.get(f"{EMAIL_CODE_PREFIX}{email}")


async def _delete_email_code(email: str) -> None:
    redis = await get_redis()
    await redis.delete(f"{EMAIL_CODE_PREFIX}{email}")


async def register_user(db: AsyncSession, email: str, password: str) -> tuple[User, str | None]:
    email = _normalize_email(email)
    validate_password_strength(password)

    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        if existing.email_verified:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email уже зарегистрирован")
        existing.password_hash = hash_password(password)
        user = existing
    else:
        user = User(
            email=email,
            password_hash=hash_password(password),
            status="pending_email",
            email_verified=False,
        )
        db.add(user)
        await db.flush()

    code = f"{secrets.randbelow(1_000_000):06d}"
    await _store_email_code(email, code)
    dev_code = await send_verification_email(email, code, locale=getattr(user, "preferred_locale", None))

    await db.commit()
    await db.refresh(user)
    return user, dev_code


async def verify_email(db: AsyncSession, email: str, code: str) -> User:
    email = _normalize_email(email)
    stored = await _get_email_code(email)
    if not stored or stored != code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неверный или просроченный код")

    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")

    user.email_verified = True
    user.status = "pending_type"
    await _delete_email_code(email)
    await db.commit()
    await db.refresh(user)
    return user


async def revoke_other_refresh_sessions(
    db: AsyncSession,
    user_id: int,
    *,
    except_jti: str | None = None,
) -> int:
    q = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked.is_(False),
    )
    if except_jti:
        q = q.where(RefreshToken.jti != except_jti)
    rows = (await db.scalars(q)).all()
    for row in rows:
        row.revoked = True
    return len(rows)


async def _notify_other_sessions_revoked(db: AsyncSession, user: User) -> None:
    from app.services import email as email_svc
    from app.services import push as push_svc
    from app.services.email_templates import render_template
    from app.services.locale import normalize_locale

    locale = normalize_locale(getattr(user, "preferred_locale", None))
    rendered = render_template("session_revoked", locale)
    title = rendered["subject"]
    body = rendered["body"]
    try:
        await push_svc.send_to_user(
            db,
            user.id,
            title,
            body,
            data={"type": "session_revoked"},
            respect_prefs=False,
            email_fallback=True,
        )
    except Exception:
        await email_svc.send_notification_email(user.email, title, body, locale=locale)


async def issue_tokens_for_user(
    db: AsyncSession, user: User, remember_me: bool = False, *, revoke_others: bool = True
) -> tuple[str, str]:
    revoked = 0
    if revoke_others:
        revoked = await revoke_other_refresh_sessions(db, user.id)
    access_token = create_access_token(user.id, role=user.staff_role or UserRole.USER.value)
    refresh_token, jti, expires_at = create_refresh_token(user.id, remember_me=remember_me)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at))
    await db.commit()
    if revoked > 0:
        await _notify_other_sessions_revoked(db, user)
    return access_token, refresh_token


async def login_user(
    db: AsyncSession, email: str, password: str, remember_me: bool = False
) -> tuple[str, str]:
    email = _normalize_email(email)
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")

    if not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Подтвердите email перед входом")

    if user.status == "blocked":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Аккаунт заблокирован")

    user.last_login_at = datetime.now(timezone.utc)
    return await issue_tokens_for_user(db, user, remember_me=remember_me)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    payload = decode_token(refresh_token, TokenType.REFRESH)
    jti = payload.get("jti")
    user_id = int(payload["sub"])

    token_row = await db.scalar(
        select(RefreshToken).where(RefreshToken.jti == jti, RefreshToken.revoked.is_(False))
    )
    if not token_row or token_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh-токен недействителен")

    user = await db.get(User, user_id)
    if not user or user.status == "blocked":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь недоступен")

    user.last_login_at = datetime.now(timezone.utc)
    token_row.revoked = True
    access_token = create_access_token(user.id, role=user.staff_role or "user")
    new_refresh, new_jti, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, jti=new_jti, expires_at=expires_at))
    await db.commit()
    return access_token, new_refresh


def _validate_inn(inn: str) -> None:
    if not inn.isdigit() or len(inn) not in (10, 12):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ИНН должен содержать 10 или 12 цифр")


async def set_account_type(db: AsyncSession, user: User, body: AccountTypeRequest) -> User:
    account_type = body.account_type
    if account_type not in ("individual", "legal"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неверный тип аккаунта")
    if user.status not in ("pending_type", "active_individual", "active_legal"):
        if not user.email_verified:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Сначала подтвердите email")

    if body.full_name:
        pii_svc.encrypt_user_fields(user, {"full_name": body.full_name.strip()})

    if account_type == "individual":
        user.account_type = "individual"
        user.status = "active_individual"
        await db.commit()
        await db.refresh(user)
        return user

    # Юрлицо / ИП
    if not body.company_name or not body.inn or not body.ogrn or not body.legal_address:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Для юрлица обязательны: наименование, ИНН, ОГРН/ОГРНИП, юридический адрес",
        )
    if not body.director_name or not body.bank_name or not body.bik or not body.checking_account:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Укажите ФИО руководителя, банк, БИК и расчётный счёт",
        )
    _validate_inn(body.inn.strip())
    ogrn = body.ogrn.strip()
    if not ogrn.isdigit() or len(ogrn) not in (13, 15):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ОГРН — 13 цифр, ОГРНИП — 15")
    checking = body.checking_account.strip()
    if not checking.isdigit() or len(checking) != 20:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Расчётный счёт — 20 цифр")

    company = Company(
        name=body.company_name.strip(),
        inn=body.inn.strip(),
        owner_id=user.id,
        status="active",
        settings=pii_svc.encrypt_company_settings(
            {
                "kpp": body.kpp,
                "ogrn": ogrn,
                "legal_address": body.legal_address,
                "actual_address": body.actual_address or body.legal_address,
                "bank_name": body.bank_name,
                "bik": body.bik,
                "checking_account": checking,
                "corr_account": body.corr_account,
                "director_name": body.director_name,
                "docs_email": body.docs_email or user.email,
                "verification": "manual_confirmed",
            }
        ),
    )
    db.add(company)
    await db.flush()
    db.add(CompanyMember(company_id=company.id, user_id=user.id, role="owner"))
    user.account_type = "legal"
    user.status = "active_legal"
    if body.director_name and not user.full_name:
        pii_svc.encrypt_user_fields(user, {"full_name": body.director_name.strip()})
    await db.commit()
    await db.refresh(user)
    return user


async def logout_user(db: AsyncSession, refresh_token: str) -> None:
    payload = decode_token(refresh_token, TokenType.REFRESH)
    jti = payload.get("jti")
    token_row = await db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if token_row:
        token_row.revoked = True
        await db.commit()


async def request_password_reset(db: AsyncSession, email: str) -> str | None:
    from app.core.config import settings

    email = _normalize_email(email)
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        return None

    token = secrets.token_urlsafe(32)
    redis = await get_redis()
    await redis.set(f"{PASSWORD_RESET_PREFIX}{token}", str(user.id), ex=settings.PASSWORD_RESET_TTL_SECONDS)
    return await send_password_reset_email(email, token, locale=getattr(user, "preferred_locale", None))


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> None:
    validate_password_strength(new_password)
    redis = await get_redis()
    user_id = await redis.get(f"{PASSWORD_RESET_PREFIX}{token}")
    if not user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неверный или просроченный токен")

    user = await db.get(User, int(user_id))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")

    user.password_hash = hash_password(new_password)
    await redis.delete(f"{PASSWORD_RESET_PREFIX}{token}")
    await db.commit()
