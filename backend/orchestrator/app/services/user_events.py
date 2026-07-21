"""§12.1 user_events taxonomy + persist/query."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserEvent

# §12.1.1 — полная taxonomy (30+ типов)
USER_EVENT_TYPES = frozenset(
    {
        "login",
        "start_shoot",
        "shoot_step_completed",
        "shoot_step_retry",
        "shoot_completed",
        "order_created",
        "order_cancelled",
        "model_generated",
        "model_downloaded",
        "model_rated",
        "publication_link_added",
        "publication_verified",
        "publication_marked",
        "restore_from_cloud",
        "calibration_performed",
        "low_confidence_ignored",
        "fallback_triggered",
        "company_invite_sent",
        "company_member_removed",
        "company_member_role_changed",
        "member_limits_changed",
        "member_blocked",
        "member_unblocked",
        "session_revoked",
        "api_key_created",
        "api_key_revoked",
        "shoot_link_created",
        "shoot_link_used",
        "company_balance_changed",
        "promocode_applied",
        "campaign_sent",
        "campaign_converted",
        "nsfw_blocked",
        "age_verification",
        "wordlist_match",
        "task_escalated",
        "worker_offline",
        "receipt_sent",
        "screen_time",
        "photographer_limit_reached",
        "api_key_rate_limit_exceeded",
        "shoot_link_expired",
        "auto_cleanup_executed",
        "forbidden_category_attempt",
    }
)


async def record_event(
    db: AsyncSession,
    *,
    event_type: str,
    user_id: int | None = None,
    company_id: int | None = None,
    member_role: str | None = None,
    payload: dict[str, Any] | None = None,
    event_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> UserEvent:
    if event_type not in USER_EVENT_TYPES:
        raise ValueError(f"unknown user event: {event_type}")
    row = UserEvent(
        event_id=event_id or uuid.uuid4(),
        user_id=user_id,
        company_id=company_id,
        member_role=member_role,
        event_type=event_type,
        payload=payload or {},
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    return row


async def export_csv(
    db: AsyncSession,
    *,
    company_id: int,
    days: int = 30,
    event_type: str | None = None,
    limit: int = 5000,
) -> str:
    """CSV export company user_events §12.7."""
    import csv
    import io
    from datetime import timedelta

    since = datetime.now(timezone.utc) - timedelta(days=days)
    data = await list_events(
        db,
        company_id=company_id,
        event_type=event_type,
        date_from=since,
        limit=limit,
        offset=0,
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["event_id", "user_id", "member_role", "event_type", "payload", "created_at"])
    for r in data["items"]:
        w.writerow(
            [
                r["event_id"],
                r["user_id"],
                r.get("member_role") or "",
                r["event_type"],
                json.dumps(r.get("payload") or {}, ensure_ascii=False),
                r.get("created_at") or "",
            ]
        )
    return buf.getvalue()


async def list_events(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    company_id: int | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 200,
    offset: int = 0,
) -> dict:
    filters = []
    if user_id is not None:
        filters.append(UserEvent.user_id == user_id)
    if company_id is not None:
        filters.append(UserEvent.company_id == company_id)
    if event_type:
        filters.append(UserEvent.event_type == event_type)
    if date_from:
        filters.append(UserEvent.created_at >= date_from)
    if date_to:
        filters.append(UserEvent.created_at <= date_to)

    count_q = select(func.count()).select_from(UserEvent)
    if filters:
        count_q = count_q.where(*filters)
    total = int(await db.scalar(count_q) or 0)

    q = select(UserEvent).order_by(UserEvent.id.desc())
    if filters:
        q = q.where(*filters)
    rows = (await db.scalars(q.offset(offset).limit(min(limit, 2000)))).all()
    return {
        "total": total,
        "items": [
            {
                "event_id": str(r.event_id),
                "user_id": r.user_id,
                "company_id": r.company_id,
                "member_role": r.member_role,
                "event_type": r.event_type,
                "payload": r.payload or {},
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
