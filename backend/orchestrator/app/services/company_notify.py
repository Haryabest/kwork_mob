"""Корпоративные настройки уведомлений Owner §3.19."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, CompanyMember, User

# audience: owner_only | owner_manager | all
EVENT_DEFAULTS: dict[str, str] = {
    "generation_done": "owner_manager",
    "photographer_uploaded": "owner_manager",
    "source_expire": "all",
    "publish_reminder": "owner_manager",
    "low_balance": "owner_only",
}

AUDIENCES = ("owner_only", "owner_manager", "all")
SETTINGS_KEY = "notification_routing"


def normalize_routing(raw: dict | None) -> dict[str, str]:
    out = dict(EVENT_DEFAULTS)
    if not raw:
        return out
    for k, v in raw.items():
        if k not in EVENT_DEFAULTS:
            continue
        val = str(v).lower().strip()
        if val in AUDIENCES:
            out[k] = val
    return out


def routing_from_company(company: Company | None) -> dict[str, str]:
    if not company:
        return dict(EVENT_DEFAULTS)
    settings = company.settings or {}
    return normalize_routing(settings.get(SETTINGS_KEY) if isinstance(settings.get(SETTINGS_KEY), dict) else {})


async def resolve_recipient_ids(
    db: AsyncSession,
    *,
    company_id: int,
    event: str,
) -> list[int]:
    """Кого уведомлять по событию согласно prefs Owner."""
    company = await db.get(Company, company_id)
    if not company:
        return []
    routing = routing_from_company(company)
    audience = routing.get(event, EVENT_DEFAULTS.get(event, "owner_manager"))
    ids: set[int] = {company.owner_id}

    if audience == "owner_only":
        return sorted(ids)

    members = (
        await db.scalars(select(CompanyMember).where(CompanyMember.company_id == company_id))
    ).all()
    for m in members:
        role = (m.role or "").lower()
        if audience == "all":
            ids.add(m.user_id)
        elif audience == "owner_manager" and role in ("owner", "manager"):
            ids.add(m.user_id)
    return sorted(ids)


async def notify_company_event(
    db: AsyncSession,
    *,
    company_id: int | None,
    event: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Push/email по routing §3.19 + user.notification_prefs."""
    if not company_id:
        return {"sent": 0, "recipients": []}
    user_ids = await resolve_recipient_ids(db, company_id=company_id, event=event)
    if not user_ids:
        return {"sent": 0, "recipients": []}

    from app.services import push as push_svc

    # фильтр по личным prefs
    pref_key = {
        "generation_done": "generation_done",
        "photographer_uploaded": "generation_done",  # reuse order-ish
        "source_expire": "source_expire",
        "publish_reminder": "publish_reminder",
        "low_balance": "email_balance",
    }.get(event)
    filtered: list[int] = []
    for uid in user_ids:
        user = await db.get(User, uid)
        if not user:
            continue
        prefs = dict(user.notification_prefs or {})
        if prefs.get("push_enabled") is False and prefs.get("email_enabled") is False:
            continue
        if pref_key and prefs.get(pref_key) is False:
            continue
        filtered.append(uid)

    if not filtered:
        return {"sent": 0, "recipients": []}

    result = await push_svc.send_to_users(
        db,
        filtered,
        title,
        body,
        data={
            **{k: str(v) for k, v in (data or {}).items()},
            "event": event,
            "company_id": str(company_id),
        },
    )
    return {
        "sent": result.get("pushed", 0) + result.get("emailed", 0),
        "recipients": filtered,
        "audience": routing_from_company(await db.get(Company, company_id)).get(event),
        **result,
    }


def merge_routing_into_settings(settings: dict | None, routing: dict | None) -> dict:
    s = dict(settings or {})
    if routing is not None:
        s[SETTINGS_KEY] = normalize_routing(routing)
    return s
