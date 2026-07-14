"""Автосоздание support ticket при yookassa_webhook_manual_review (§8.1 / §20.7)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SupportMessage, SupportRequest, User

logger = logging.getLogger(__name__)

CATEGORY = "payment"
SUBJECT_PREFIX = "[YooKassa] Manual review"


async def create_manual_review_ticket(
    db: AsyncSession,
    *,
    order_id: str | int | None,
    payment_id: str | None,
    streak: int,
    detail: str = "",
    user_id: int | None = None,
    company_id: int | None = None,
) -> dict[str, Any]:
    """
    Тикет для staff при fail streak ≥5.
    Идемпотентность: не дублируем открытый тикет по тому же order/payment за 48ч.
    """
    subject = f"{SUBJECT_PREFIX} order={order_id or '—'} payment={payment_id or '—'}"
    since = datetime.now(timezone.utc) - timedelta(hours=48)
    existing = (
        await db.scalars(
            select(SupportRequest)
            .where(
                SupportRequest.category == CATEGORY,
                SupportRequest.subject == subject,
                SupportRequest.created_at >= since,
                SupportRequest.status.in_(("new", "in_progress")),
            )
            .limit(1)
        )
    ).first()
    if existing:
        return {"created": False, "ticket_id": existing.id, "reason": "exists"}

    uid = user_id
    if uid is None:
        # fallback: любой staff admin, иначе первый пользователь
        staff = await db.scalar(select(User).where(User.staff_role.isnot(None)).limit(1))
        if staff:
            uid = staff.id
        else:
            any_user = await db.scalar(select(User).order_by(User.id).limit(1))
            uid = any_user.id if any_user else None
    if uid is None:
        logger.warning("manual_review ticket skipped: no user")
        return {"created": False, "reason": "no_user"}

    body = (
        f"Требуется ручная проверка платежа ЮKassa (§8.1).\n\n"
        f"order_id: {order_id}\n"
        f"payment_id: {payment_id}\n"
        f"company_id: {company_id}\n"
        f"fail_streak: {streak}\n"
        f"detail: {(detail or '')[:500]}\n\n"
        f"Источник: audit yookassa_webhook_manual_review"
    )
    req = SupportRequest(
        user_id=uid,
        subject=subject[:255],
        category=CATEGORY,
        message=body,
        status="new",
        attachments=[],
    )
    db.add(req)
    await db.flush()
    db.add(
        SupportMessage(
            request_id=req.id,
            author_id=uid,
            is_staff=False,
            body=body,
        )
    )
    await db.flush()
    return {"created": True, "ticket_id": req.id, "user_id": uid}
