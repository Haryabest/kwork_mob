"""Массовое создание shoot-links >100/ч → email + временная блокировка (§12.4.1)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AlertLog, Company, ShootLink
from app.services import alerts as alerts_svc

logger = logging.getLogger(__name__)

EVENT = "shoot_link_mass_create"


def _limit_per_hour() -> int:
    return int(getattr(settings, "SHOOT_LINK_MASS_LIMIT_PER_HOUR", 100) or 100)


def _block_hours() -> int:
    return int(getattr(settings, "SHOOT_LINK_MASS_BLOCK_HOURS", 1) or 1)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_blocked_until(settings_map: dict) -> datetime | None:
    raw = settings_map.get("shoot_link_blocked_until")
    if not raw:
        return None
    try:
        until = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None
    return _aware(until)


def clear_block_if_expired(company: Company) -> bool:
    """Сброс shoot_link_blocked_until после истечения. True если сняли."""
    settings_map = dict(company.settings or {})
    until = _parse_blocked_until(settings_map)
    if until is None:
        return False
    if until > datetime.now(timezone.utc):
        return False
    settings_map.pop("shoot_link_blocked_until", None)
    settings_map.pop("shoot_link_block_reason", None)
    settings_map["shoot_link_unblocked_at"] = datetime.now(timezone.utc).isoformat()
    company.settings = settings_map
    return True


def is_shoot_link_blocked(company: Company | None) -> datetime | None:
    """Возвращает until если блокировка активна (после auto-unblock expired)."""
    if not company:
        return None
    clear_block_if_expired(company)
    settings_map = dict(company.settings or {})
    until = _parse_blocked_until(settings_map)
    if until and until > datetime.now(timezone.utc):
        return until
    return None


async def clear_expired_blocks(db: AsyncSession) -> dict[str, Any]:
    """Celery: снять истёкшие блокировки shoot-link у всех компаний."""
    rows = (await db.scalars(select(Company))).all()
    cleared = 0
    for company in rows:
        settings_map = company.settings or {}
        if not settings_map.get("shoot_link_blocked_until"):
            continue
        if clear_block_if_expired(company):
            cleared += 1
    if cleared:
        await db.flush()
    return {"cleared": cleared, "scanned": len(rows)}


async def assert_can_create(db: AsyncSession, *, company_id: int | None) -> dict[str, Any]:
    """
    Проверка лимита и блокировки перед созданием ссылки.
    При превышении — email + временная блокировка компании.
    """
    if company_id is None:
        return {"ok": True, "count": 0}

    from app.services import alert_thresholds as ath

    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")

    until = is_shoot_link_blocked(company)
    limit = int(await ath.threshold_async("shoot_link_mass_limit_per_hour", _limit_per_hour()))
    block_h = int(await ath.threshold_async("shoot_link_mass_block_hours", _block_hours()))
    if until:
        raise HTTPException(
            429,
            f"Создание shoot-link временно заблокировано до {until.isoformat()} "
            f"(массовое создание >{limit}/ч)",
        )

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    cnt = int(
        await db.scalar(
            select(func.count())
            .select_from(ShootLink)
            .where(ShootLink.company_id == company_id, ShootLink.created_at >= since)
        )
        or 0
    )
    # блокируем когда уже достигли лимита (следующая будет 101-й)
    if cnt >= limit:
        block_until = datetime.now(timezone.utc) + timedelta(hours=block_h)
        settings_map = dict(company.settings or {})
        settings_map["shoot_link_blocked_until"] = block_until.isoformat()
        settings_map["shoot_link_block_reason"] = "mass_create"
        company.settings = settings_map

        fp = f"mass_shoot:{company_id}:{since.replace(minute=0, second=0, microsecond=0).isoformat()}"
        recent = (
            await db.scalars(
                select(AlertLog)
                .where(AlertLog.event_type == EVENT, AlertLog.ok.is_(True))
                .order_by(AlertLog.id.desc())
                .limit(20)
            )
        ).all()
        already = any((r.payload or {}).get("fingerprint") == fp for r in recent)
        if not already:
            text = (
                f"⚠️ Массовое создание shoot-links\n"
                f"company_id: {company_id}\n"
                f"name: {company.name}\n"
                f"created_1h: {cnt}\n"
                f"limit: {limit}\n"
                f"blocked_until: {block_until.isoformat()}"
            )
            await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT,
                payload={
                    "fingerprint": fp,
                    "company_id": company_id,
                    "count": cnt,
                    "limit": limit,
                    "blocked_until": block_until.isoformat(),
                },
                subject=f"[3dvektor] Mass shoot-links company={company_id}",
                telegram=False,
                email=True,
            )
        await db.flush()
        raise HTTPException(
            429,
            f"Превышен лимит {limit} shoot-link/час. "
            f"Временная блокировка до {block_until.isoformat()}",
        )

    return {"ok": True, "count": cnt, "limit": limit}
