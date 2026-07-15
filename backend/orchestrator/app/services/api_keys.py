"""B2B API-ключи §8.8 / §15.6."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, CompanyApiKey, User

ALLOWED_SCOPES = {
    "order:create",
    "order:read",
    "import:create",
    "balance:read",
    "member:list",
    "shoot_link:create",
}


def hash_key(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_key(plain: str, key_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), key_hash.encode())
    except Exception:  # noqa: BLE001
        return False


def generate_key() -> tuple[str, str, str]:
    """Возвращает (plaintext, prefix, hash)."""
    raw = secrets.token_urlsafe(32)
    plain = f"kw_{raw}"
    prefix = plain[:12]
    return plain, prefix, hash_key(plain)


async def require_company_owner(db: AsyncSession, user: User) -> Company:
    """Совместимость: Owner или участник с can_manage_api_keys."""
    from app.services.access import company_for_permission

    return await company_for_permission(db, user, "can_manage_api_keys")


def _effective_daily_limit(row_limit: int | None) -> int:
    from app.services.api_key_limits import default_daily_limit

    if row_limit is not None and int(row_limit) > 0:
        return int(row_limit)
    return default_daily_limit()


async def create_key(
    db: AsyncSession,
    *,
    user: User,
    name: str,
    scopes: list[str],
    rate_limit_per_min: int = 1000,
    daily_limit: int | None = None,
) -> tuple[CompanyApiKey, str]:
    from app.models import AuditLog

    company = await require_company_owner(db, user)
    scopes = [s for s in scopes if s in ALLOWED_SCOPES]
    if not scopes:
        raise HTTPException(400, f"scopes из: {', '.join(sorted(ALLOWED_SCOPES))}")
    plain, prefix, kh = generate_key()
    eff_daily = _effective_daily_limit(daily_limit)
    row = CompanyApiKey(
        company_id=company.id,
        name=name[:100],
        key_prefix=prefix,
        key_hash=kh,
        scopes=scopes,
        rate_limit_per_min=max(10, min(rate_limit_per_min, 10000)),
        daily_limit=eff_daily,
        is_active=True,
        created_by_user_id=user.id,
    )
    db.add(row)
    await db.flush()
    db.add(
        AuditLog(
            company_id=company.id,
            user_id=user.id,
            action="api_key_created",
            details={
                "key_id": row.id,
                "key_prefix": prefix,
                "scopes": scopes,
                "name": row.name,
                "daily_limit": eff_daily,
            },
        )
    )
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        await redis.set(f"rl:apikey:cfg:{prefix}", str(row.rate_limit_per_min), ex=86400)
        await redis.set(f"rl:apikey:daily_cfg:{prefix}", str(eff_daily), ex=86400 * 7)
    except Exception:  # noqa: BLE001
        pass
    return row, plain


async def list_keys(db: AsyncSession, user: User) -> list[dict]:
    company = await require_company_owner(db, user)
    rows = (
        await db.scalars(
            select(CompanyApiKey)
            .where(CompanyApiKey.company_id == company.id)
            .order_by(CompanyApiKey.id.desc())
        )
    ).all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": k.scopes,
            "rate_limit_per_min": k.rate_limit_per_min,
            "daily_limit": k.daily_limit or _effective_daily_limit(None),
            "is_active": k.is_active,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
        }
        for k in rows
    ]


async def revoke_key(db: AsyncSession, user: User, key_id: int) -> None:
    from app.models import AuditLog

    company = await require_company_owner(db, user)
    row = await db.get(CompanyApiKey, key_id)
    if not row or row.company_id != company.id:
        raise HTTPException(404, "Ключ не найден")
    row.is_active = False
    row.revoked_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            company_id=company.id,
            user_id=user.id,
            action="api_key_revoked",
            details={"key_id": row.id, "key_prefix": row.key_prefix, "name": row.name},
        )
    )
    await db.flush()


async def authenticate_api_key(db: AsyncSession, plain: str) -> tuple[CompanyApiKey, Company, User]:
    if not plain or not plain.startswith("kw_"):
        raise HTTPException(401, "Неверный API-ключ")
    prefix = plain[:12]
    candidates = (
        await db.scalars(
            select(CompanyApiKey).where(
                CompanyApiKey.key_prefix == prefix,
                CompanyApiKey.is_active.is_(True),
            )
        )
    ).all()
    row = None
    for c in candidates:
        if verify_key(plain, c.key_hash):
            row = c
            break
    if not row:
        raise HTTPException(401, "Неверный API-ключ")
    company = await db.get(Company, row.company_id)
    if not company:
        raise HTTPException(401, "Компания не найдена")
    owner = await db.get(User, company.owner_id)
    if not owner:
        raise HTTPException(401, "Owner не найден")
    row.last_used_at = datetime.now(timezone.utc)
    await db.flush()
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        await redis.set(f"rl:apikey:cfg:{row.key_prefix}", str(row.rate_limit_per_min), ex=86400)
        await redis.set(
            f"rl:apikey:daily_cfg:{row.key_prefix}",
            str(_effective_daily_limit(row.daily_limit)),
            ex=86400 * 7,
        )
    except Exception:  # noqa: BLE001
        pass
    return row, company, owner
