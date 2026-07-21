"""Авто-блокировка неактивных сотрудников B2B (§2.5.4 auto_block_inactive_days)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, CompanyMember, RefreshToken, User
from app.services.company_members import audit
from app.services.company_policies import policies_for_company

OWNER_ROLES = frozenset({"owner"})


def effective_last_login(user: User) -> datetime | None:
    """Последняя активность: last_login_at или дата регистрации."""
    ts = user.last_login_at or user.created_at
    if ts and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def is_auto_block_exempt(
    *,
    company: Company,
    member: CompanyMember,
    user_id: int,
    policies: dict[str, Any],
) -> bool:
    """Owner и явные исключения в политике не блокируются."""
    if user_id == company.owner_id:
        return True
    if (member.role or "").lower() in OWNER_ROLES:
        return True
    exempt = policies.get("auto_block_exempt_user_ids") or []
    if isinstance(exempt, list) and user_id in exempt:
        return True
    return False


def should_block_member(
    *,
    last_active: datetime | None,
    cutoff: datetime,
    user_status: str,
) -> bool:
    if user_status in ("blocked", "blocked_permanent", "blocked_pending_review", "deleted"):
        return False
    if not last_active:
        return False
    if last_active.tzinfo is None:
        last_active = last_active.replace(tzinfo=timezone.utc)
    return last_active < cutoff


async def block_inactive_company_members(db: AsyncSession) -> dict[str, Any]:
    """Для каждой компании: неактивные сотрудники → user.status=blocked + audit."""
    now = datetime.now(timezone.utc)
    companies = (await db.scalars(select(Company).where(Company.status == "active"))).all()
    blocked_users = 0
    companies_processed = 0
    details: list[dict[str, Any]] = []

    for company in companies:
        policies = policies_for_company(company)
        days = int(policies.get("auto_block_inactive_days") or 0)
        if days <= 0:
            continue
        companies_processed += 1
        cutoff = now - timedelta(days=days)

        members = (
            await db.scalars(select(CompanyMember).where(CompanyMember.company_id == company.id))
        ).all()

        for member in members:
            user = await db.get(User, member.user_id)
            if not user:
                continue
            if is_auto_block_exempt(
                company=company,
                member=member,
                user_id=user.id,
                policies=policies,
            ):
                continue

            last_active = effective_last_login(user)
            if not should_block_member(
                last_active=last_active,
                cutoff=cutoff,
                user_status=user.status,
            ):
                continue

            user.status = "blocked"
            tokens = (
                await db.scalars(
                    select(RefreshToken).where(
                        RefreshToken.user_id == user.id,
                        RefreshToken.revoked.is_(False),
                    )
                )
            ).all()
            for token in tokens:
                token.revoked = True

            await audit(
                db,
                company_id=company.id,
                user_id=company.owner_id,
                action="member.auto_block_inactive",
                details={
                    "blocked_user_id": user.id,
                    "role": member.role,
                    "inactive_days": days,
                    "last_active": last_active.isoformat() if last_active else None,
                },
            )
            blocked_users += 1
            details.append(
                {
                    "company_id": company.id,
                    "user_id": user.id,
                    "role": member.role,
                    "last_active": last_active.isoformat() if last_active else None,
                }
            )

    await db.commit()
    return {
        "companies_processed": companies_processed,
        "blocked_users": blocked_users,
        "items": details[:100],
    }


async def run_auto_block_inactive_once() -> dict[str, Any]:
    from app.core.database import async_session

    async with async_session() as db:
        return await block_inactive_company_members(db)
