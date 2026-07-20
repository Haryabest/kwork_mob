"""OAuth login/register business logic."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.models import AuditLog, User, UserOAuthIdentity
from app.services import auth as auth_service
from app.services import oauth_providers as op
from app.services.legal import record_consents

OAUTH_STATE_PREFIX = "oauth_state:"
REQUIRED_CONSENTS = frozenset({"terms", "privacy", "offer", "rights", "nsfw_rules"})


async def _audit_oauth(
    db: AsyncSession,
    *,
    user_id: int,
    action: str,
    provider: str,
    platform: str | None = None,
) -> None:
    details: dict = {"provider": provider}
    if platform:
        details["platform"] = platform
    db.add(AuditLog(user_id=user_id, action=action, details=details))


def default_redirect_uri(platform: str) -> str:
    if platform == "mobile":
        return settings.MOBILE_OAUTH_REDIRECT_URI
    return f"{settings.SELLER_PUBLIC_URL.rstrip('/')}/auth/oauth/callback"


async def _store_state(
    state: str,
    *,
    provider: str,
    redirect_uri: str,
    mode: str,
    consents: list[str] | None,
    user_id: int | None = None,
    platform: str = "web",
) -> None:
    redis = await get_redis()
    payload = {
        "provider": provider,
        "redirect_uri": redirect_uri,
        "mode": mode,
        "consents": consents or [],
        "user_id": user_id,
        "platform": platform,
    }
    await redis.set(
        f"{OAUTH_STATE_PREFIX}{state}",
        json.dumps(payload),
        ex=settings.OAUTH_STATE_TTL_SECONDS,
    )


async def _pop_state(state: str) -> dict:
    redis = await get_redis()
    key = f"{OAUTH_STATE_PREFIX}{state}"
    raw = await redis.get(key)
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неверный или просроченный state")
    await redis.delete(key)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неверный state") from exc
    return data


async def start_oauth(
    provider: str,
    *,
    redirect_uri: str | None,
    platform: str,
    mode: str,
    consents: list[str] | None,
) -> dict:
    if provider not in op.OAUTH_PROVIDERS:
        raise HTTPException(400, "Неизвестный провайдер")
    cfg = op.provider_config(provider)
    if not cfg:
        raise HTTPException(503, f"Провайдер {provider} не настроен")
    if mode not in {"login", "register"}:
        raise HTTPException(400, "mode должен быть login или register")
    if mode == "register":
        if not consents or not REQUIRED_CONSENTS.issubset(set(consents)):
            raise HTTPException(422, "Для регистрации нужны все обязательные согласия")
    uri = redirect_uri or default_redirect_uri(platform)
    state = secrets.token_urlsafe(24)
    await _store_state(
        state,
        provider=provider,
        redirect_uri=uri,
        mode=mode,
        consents=consents,
        platform=platform,
    )
    return {"authorize_url": op.build_authorize_url(cfg, redirect_uri=uri, state=state), "state": state}


async def _find_or_create_user(
    db: AsyncSession,
    *,
    provider: str,
    provider_user_id: str,
    email: str,
    full_name: str | None,
    profile: dict,
    mode: str,
    consents: list[str],
    ip: str | None,
    user_agent: str | None,
) -> User:
    identity = await db.scalar(
        select(UserOAuthIdentity).where(
            UserOAuthIdentity.provider == provider,
            UserOAuthIdentity.provider_user_id == provider_user_id,
        )
    )
    if identity:
        user = await db.get(User, identity.user_id)
        if not user or user.status in ("blocked", "deleted"):
            raise HTTPException(403, "Аккаунт недоступен")
        identity.email = email
        identity.profile = profile
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(user)
        return user

    email_norm = email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email_norm))
    if user:
        if user.status in ("blocked", "deleted"):
            raise HTTPException(403, "Аккаунт недоступен")
    else:
        if mode != "register":
            raise HTTPException(
                404,
                "Аккаунт не найден. Зарегистрируйтесь через соцсеть или email.",
            )
        user = User(
            email=email_norm,
            password_hash=None,
            full_name=full_name or None,
            status="pending_type",
            email_verified=True,
        )
        db.add(user)
        await db.flush()
        await record_consents(db, user.id, consents, ip, user_agent)

    db.add(
        UserOAuthIdentity(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email_norm,
            profile=profile,
        )
    )
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


async def complete_oauth(
    db: AsyncSession,
    provider: str,
    *,
    code: str,
    state: str,
    redirect_uri: str | None,
    ip: str | None,
    user_agent: str | None,
) -> tuple[User, str, str]:
    if provider not in op.OAUTH_PROVIDERS:
        raise HTTPException(400, "Неизвестный провайдер")
    cfg = op.provider_config(provider)
    if not cfg:
        raise HTTPException(503, f"Провайдер {provider} не настроен")

    stored = await _pop_state(state)
    if stored.get("provider") != provider:
        raise HTTPException(400, "state не соответствует провайдеру")
    uri = redirect_uri or stored.get("redirect_uri") or default_redirect_uri("web")
    if stored.get("redirect_uri") and redirect_uri and stored["redirect_uri"] != redirect_uri:
        raise HTTPException(400, "redirect_uri не совпадает")

    try:
        token_payload = await op.exchange_code(cfg, code=code, redirect_uri=uri)
        profile_raw = await op.fetch_profile(cfg, token_payload)
    except Exception as exc:
        raise HTTPException(502, f"Ошибка OAuth: {exc}") from exc

    provider_user_id, email, full_name = op.parse_profile(provider, profile_raw)
    if not provider_user_id:
        raise HTTPException(502, "Провайдер не вернул идентификатор пользователя")
    if not email:
        raise HTTPException(502, "Провайдер не вернул email")

    user = await _find_or_create_user(
        db,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
        full_name=full_name or None,
        profile=profile_raw,
        mode=str(stored.get("mode") or "login"),
        consents=list(stored.get("consents") or []),
        ip=ip,
        user_agent=user_agent,
    )
    platform = str(stored.get("platform") or "web")
    if platform == "web":
        from app.services.analytics_ingest import record_screen_event

        await record_screen_event(db, user_id=user.id, screen=f"oauth_login_{provider}")
    await _audit_oauth(db, user_id=user.id, action="oauth_login", provider=provider, platform=platform)
    await db.commit()
    access, refresh = await auth_service.issue_tokens_for_user(db, user, remember_me=True)
    return user, access, refresh


async def list_oauth_identities(db: AsyncSession, user_id: int) -> list[dict]:
    rows = (
        await db.scalars(
            select(UserOAuthIdentity)
            .where(UserOAuthIdentity.user_id == user_id)
            .order_by(UserOAuthIdentity.provider)
        )
    ).all()
    return [
        {
            "provider": r.provider,
            "email": r.email,
            "linked_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


async def start_oauth_link(
    user_id: int,
    provider: str,
    *,
    redirect_uri: str | None,
    platform: str,
) -> dict:
    if provider not in op.OAUTH_PROVIDERS:
        raise HTTPException(400, "Неизвестный провайдер")
    cfg = op.provider_config(provider)
    if not cfg:
        raise HTTPException(503, f"Провайдер {provider} не настроен")
    uri = redirect_uri or default_redirect_uri(platform)
    state = secrets.token_urlsafe(24)
    await _store_state(
        state,
        provider=provider,
        redirect_uri=uri,
        mode="link",
        consents=None,
        user_id=user_id,
        platform=platform,
    )
    return {"authorize_url": op.build_authorize_url(cfg, redirect_uri=uri, state=state), "state": state}


async def complete_oauth_link(
    db: AsyncSession,
    user: User,
    provider: str,
    *,
    code: str,
    state: str,
    redirect_uri: str | None,
) -> dict:
    if provider not in op.OAUTH_PROVIDERS:
        raise HTTPException(400, "Неизвестный провайдер")
    cfg = op.provider_config(provider)
    if not cfg:
        raise HTTPException(503, f"Провайдер {provider} не настроен")

    stored = await _pop_state(state)
    if stored.get("provider") != provider:
        raise HTTPException(400, "state не соответствует провайдеру")
    if stored.get("mode") != "link":
        raise HTTPException(400, "Неверный режим OAuth")
    if int(stored.get("user_id") or 0) != user.id:
        raise HTTPException(403, "state не соответствует пользователю")
    uri = redirect_uri or stored.get("redirect_uri") or default_redirect_uri("web")
    if stored.get("redirect_uri") and redirect_uri and stored["redirect_uri"] != redirect_uri:
        raise HTTPException(400, "redirect_uri не совпадает")

    try:
        token_payload = await op.exchange_code(cfg, code=code, redirect_uri=uri)
        profile_raw = await op.fetch_profile(cfg, token_payload)
    except Exception as exc:
        raise HTTPException(502, f"Ошибка OAuth: {exc}") from exc

    provider_user_id, email, _full_name = op.parse_profile(provider, profile_raw)
    if not provider_user_id:
        raise HTTPException(502, "Провайдер не вернул идентификатор пользователя")

    existing = await db.scalar(
        select(UserOAuthIdentity).where(
            UserOAuthIdentity.provider == provider,
            UserOAuthIdentity.provider_user_id == provider_user_id,
        )
    )
    if existing:
        if existing.user_id != user.id:
            raise HTTPException(409, "Этот аккаунт соцсети уже привязан к другому пользователю")
        existing.profile = profile_raw
        if email:
            existing.email = email.strip().lower()
        platform = str(stored.get("platform") or "web")
        if platform == "web":
            from app.services.analytics_ingest import record_screen_event

            await record_screen_event(db, user_id=user.id, screen=f"oauth_link_{provider}")
        await _audit_oauth(db, user_id=user.id, action="oauth_link", provider=provider, platform=platform)
        await db.commit()
        return {"linked": True, "provider": provider}

    already = await db.scalar(
        select(UserOAuthIdentity).where(
            UserOAuthIdentity.user_id == user.id,
            UserOAuthIdentity.provider == provider,
        )
    )
    if already:
        raise HTTPException(409, f"Провайдер {provider} уже привязан")

    email_norm = (email or user.email).strip().lower()
    db.add(
        UserOAuthIdentity(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email_norm,
            profile=profile_raw,
        )
    )
    platform = str(stored.get("platform") or "web")
    if platform == "web":
        from app.services.analytics_ingest import record_screen_event

        await record_screen_event(db, user_id=user.id, screen=f"oauth_link_{provider}")
    await _audit_oauth(db, user_id=user.id, action="oauth_link", provider=provider, platform=platform)
    await db.commit()
    return {"linked": True, "provider": provider}


async def unlink_oauth(db: AsyncSession, user: User, provider: str) -> dict:
    if provider not in op.OAUTH_PROVIDERS:
        raise HTTPException(400, "Неизвестный провайдер")
    identity = await db.scalar(
        select(UserOAuthIdentity).where(
            UserOAuthIdentity.user_id == user.id,
            UserOAuthIdentity.provider == provider,
        )
    )
    if not identity:
        raise HTTPException(404, "Привязка не найдена")

    other = await db.scalar(
        select(UserOAuthIdentity.id).where(
            UserOAuthIdentity.user_id == user.id,
            UserOAuthIdentity.provider != provider,
        )
    )
    if not user.password_hash and not other:
        raise HTTPException(
            400,
            "Нельзя отвязать единственный способ входа. Сначала задайте пароль.",
        )

    await _audit_oauth(db, user_id=user.id, action="oauth_unlink", provider=provider)
    await db.delete(identity)
    await db.commit()
    return {"unlinked": True, "provider": provider}
