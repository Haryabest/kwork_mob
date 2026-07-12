"""B2B API-ключи §8.8 / §15.6."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, CompanyApiKey, CompanyMember, User

ALLOWED_SCOPES = {
    "order:create",
    "order:read",
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
    company = await db.scalar(select(Company).where(Company.owner_id == user.id).limit(1))
    if not company:
        raise HTTPException(403, "Только Owner компании может управлять API-ключами")
    return company


async def create_key(
    db: AsyncSession,
    *,
    user: User,
    name: str,
    scopes: list[str],
    rate_limit_per_min: int = 1000,
) -> tuple[CompanyApiKey, str]:
    company = await require_company_owner(db, user)
    scopes = [s for s in scopes if s in ALLOWED_SCOPES]
    if not scopes:
        raise HTTPException(400, f"scopes из: {', '.join(sorted(ALLOWED_SCOPES))}")
    plain, prefix, kh = generate_key()
    row = CompanyApiKey(
        company_id=company.id,
        name=name[:100],
        key_prefix=prefix,
        key_hash=kh,
        scopes=scopes,
        rate_limit_per_min=max(10, min(rate_limit_per_min, 10000)),
        is_active=True,
        created_by_user_id=user.id,
    )
    db.add(row)
    await db.flush()
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        await redis.set(f"rl:apikey:cfg:{prefix}", str(row.rate_limit_per_min), ex=86400)
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
            "is_active": k.is_active,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
        }
        for k in rows
    ]


async def revoke_key(db: AsyncSession, user: User, key_id: int) -> None:
    company = await require_company_owner(db, user)
    row = await db.get(CompanyApiKey, key_id)
    if not row or row.company_id != company.id:
        raise HTTPException(404, "Ключ не найден")
    row.is_active = False
    row.revoked_at = datetime.now(timezone.utc)
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
    except Exception:  # noqa: BLE001
        pass
    return row, company, owner
