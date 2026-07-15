"""Inbox уведомлений пользователя §19.16."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserNotification

MAX_INBOX = 200


async def record(
    db: AsyncSession,
    *,
    user_id: int,
    title: str,
    body: str,
    event_type: str | None = None,
    order_id: int | None = None,
    model_uuid: str | None = None,
    dedup_key: str | None = None,
) -> UserNotification | None:
    if dedup_key:
        existing = await db.scalar(
            select(UserNotification).where(
                UserNotification.user_id == user_id,
                UserNotification.dedup_key == dedup_key,
            )
        )
        if existing:
            return existing
    row = UserNotification(
        user_id=user_id,
        dedup_key=dedup_key,
        event_type=event_type,
        title=title[:255],
        body=body[:2000],
        order_id=order_id,
        model_uuid=model_uuid,
    )
    db.add(row)
    await db.flush()
    # trim old
    cnt = await db.scalar(
        select(func.count()).select_from(UserNotification).where(UserNotification.user_id == user_id)
    )
    if cnt and cnt > MAX_INBOX:
        old_ids = (
            await db.scalars(
                select(UserNotification.id)
                .where(UserNotification.user_id == user_id)
                .order_by(UserNotification.id.asc())
                .limit(int(cnt) - MAX_INBOX)
            )
        ).all()
        if old_ids:
            for oid in old_ids:
                obj = await db.get(UserNotification, oid)
                if obj:
                    await db.delete(obj)
    return row


async def list_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[UserNotification], int]:
    total = await db.scalar(
        select(func.count()).select_from(UserNotification).where(UserNotification.user_id == user_id)
    ) or 0
    rows = (
        await db.scalars(
            select(UserNotification)
            .where(UserNotification.user_id == user_id)
            .order_by(UserNotification.id.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return rows, int(total)


async def unread_count(db: AsyncSession, user_id: int) -> int:
    return int(
        await db.scalar(
            select(func.count()).where(
                UserNotification.user_id == user_id,
                UserNotification.read_at.is_(None),
            )
        )
        or 0
    )


async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> bool:
    row = await db.get(UserNotification, notification_id)
    if not row or row.user_id != user_id:
        return False
    if not row.read_at:
        row.read_at = datetime.now(timezone.utc)
    return True


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    rows = (
        await db.scalars(
            select(UserNotification).where(
                UserNotification.user_id == user_id,
                UserNotification.read_at.is_(None),
            )
        )
    ).all()
    now = datetime.now(timezone.utc)
    for r in rows:
        r.read_at = now
    return len(rows)


async def clear_all(db: AsyncSession, user_id: int) -> int:
    rows = (
        await db.scalars(select(UserNotification).where(UserNotification.user_id == user_id))
    ).all()
    for r in rows:
        await db.delete(r)
    return len(rows)
