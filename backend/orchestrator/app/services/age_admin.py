"""Админ: просмотр age-gate проверок (§10.8.3 / §11 модерация)."""

from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User
from app.services.age_gate import age_years


async def list_age_verifications(
    db: AsyncSession,
    *,
    limit: int = 200,
    success: bool | None = None,
) -> dict[str, Any]:
    q = (
        select(AuditLog)
        .where(AuditLog.action == "age_verification")
        .order_by(AuditLog.id.desc())
        .limit(min(limit, 1000))
    )
    rows = (await db.scalars(q)).all()
    items = []
    for r in rows:
        details = r.details or {}
        ok = details.get("success")
        if success is not None and bool(ok) != success:
            continue
        u = await db.get(User, r.user_id) if r.user_id else None
        items.append(
            {
                "id": r.id,
                "user_id": r.user_id,
                "email": u.email if u else None,
                "age": details.get("age"),
                "success": bool(ok),
                "category": details.get("category"),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "user_age_verified_at": u.age_verified_at.isoformat() if u and u.age_verified_at else None,
                "date_of_birth": u.date_of_birth.isoformat() if u and u.date_of_birth else None,
            }
        )

    verified_users = (
        await db.scalars(
            select(User)
            .where(User.age_verified_at.is_not(None))
            .order_by(User.age_verified_at.desc())
            .limit(100)
        )
    ).all()
    users = [
        {
            "user_id": u.id,
            "email": u.email,
            "date_of_birth": u.date_of_birth.isoformat() if u.date_of_birth else None,
            "age_years": age_years(u.date_of_birth) if u.date_of_birth else None,
            "age_verified_at": u.age_verified_at.isoformat() if u.age_verified_at else None,
            "status": u.status,
        }
        for u in verified_users
    ]
    failed = sum(1 for i in items if not i["success"])
    passed = sum(1 for i in items if i["success"])
    return {
        "summary": {"events": len(items), "passed": passed, "failed": failed, "verified_users": len(users)},
        "events": items,
        "verified_users": users,
    }


def to_csv(events: list[dict[str, Any]]) -> str:
    """CSV экспорт проверок возраста (§11)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "user_id", "email", "age", "success", "category", "created_at", "date_of_birth", "age_verified_at"]
    )
    for e in events:
        writer.writerow(
            [
                e.get("id"),
                e.get("user_id"),
                e.get("email") or "",
                e.get("age") if e.get("age") is not None else "",
                "1" if e.get("success") else "0",
                e.get("category") or "",
                e.get("created_at") or "",
                e.get("date_of_birth") or "",
                e.get("user_age_verified_at") or "",
            ]
        )
    return buf.getvalue()
