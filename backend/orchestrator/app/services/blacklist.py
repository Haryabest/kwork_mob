"""CRUD чёрного списка слов/брендов (§10.8 / §11)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, ModerationBlacklist
from app.services.nsfw import DEFAULT_BLACKLIST


async def list_words(
    db: AsyncSession,
    *,
    active_only: bool = True,
    limit: int = 500,
) -> list[dict[str, Any]]:
    q = select(ModerationBlacklist).order_by(ModerationBlacklist.word.asc()).limit(min(limit, 2000))
    if active_only:
        q = q.where(ModerationBlacklist.is_active.is_(True))
    rows = (await db.scalars(q)).all()
    return [
        {
            "id": r.id,
            "word": r.word,
            "category": r.category,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


async def active_word_set(db: AsyncSession) -> set[str]:
    rows = (
        await db.scalars(
            select(ModerationBlacklist.word).where(ModerationBlacklist.is_active.is_(True))
        )
    ).all()
    words = {str(w).lower() for w in rows}
    if not words:
        words = {w.lower() for w in DEFAULT_BLACKLIST}
    return words


async def add_word(
    db: AsyncSession,
    *,
    word: str,
    category: str,
    admin_id: int | None,
) -> ModerationBlacklist:
    cleaned = (word or "").strip().lower()
    if len(cleaned) < 2:
        raise HTTPException(400, "Слово слишком короткое")
    if len(cleaned) > 120:
        raise HTTPException(400, "Слово слишком длинное")
    cat = (category or "general").strip().lower()[:32]
    existing = await db.scalar(
        select(ModerationBlacklist).where(ModerationBlacklist.word == cleaned)
    )
    if existing:
        existing.is_active = True
        existing.category = cat
        row = existing
    else:
        row = ModerationBlacklist(
            word=cleaned,
            category=cat,
            is_active=True,
            created_by_user_id=admin_id,
        )
        db.add(row)
        await db.flush()
    db.add(
        AuditLog(
            user_id=admin_id,
            action="blacklist_word_added",
            details={"word": cleaned, "category": cat, "id": row.id},
        )
    )
    await db.flush()
    return row


async def remove_word(db: AsyncSession, *, word_id: int, admin_id: int | None) -> None:
    row = await db.get(ModerationBlacklist, word_id)
    if not row:
        raise HTTPException(404, "Слово не найдено")
    row.is_active = False
    db.add(
        AuditLog(
            user_id=admin_id,
            action="blacklist_word_removed",
            details={"word": row.word, "id": row.id},
        )
    )
    await db.flush()
