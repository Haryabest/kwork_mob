"""Корпоративные алерты §12.4.1: no photographer / low balance / suspicious orders."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AlertLog, Company, CompanyMember, Order
from app.services import alerts as alerts_svc

logger = logging.getLogger(__name__)

EVENT_NO_PHOTO = "company_no_photographer"
EVENT_LOW_BALANCE = "company_low_balance"
EVENT_SUSPICIOUS = "company_suspicious_orders"


def _low_balance_threshold() -> int:
    return int(getattr(settings, "COMPANY_LOW_BALANCE_ALERT_RUB", 5000) or 5000)


def _suspicious_orders() -> int:
    return int(getattr(settings, "COMPANY_SUSPICIOUS_ORDERS_10M", 50) or 50)


def _suspicious_window_min() -> int:
    return int(getattr(settings, "COMPANY_SUSPICIOUS_WINDOW_MIN", 10) or 10)


async def _recent_ok(db: AsyncSession, event_type: str, fingerprint: str, *, hours: float = 12) -> bool:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        await db.scalars(
            select(AlertLog)
            .where(
                AlertLog.event_type == event_type,
                AlertLog.ok.is_(True),
                AlertLog.created_at >= since,
            )
            .order_by(AlertLog.id.desc())
            .limit(40)
        )
    ).all()
    for r in rows:
        if (r.payload or {}).get("fingerprint") == fingerprint:
            return True
    return False


async def alert_no_photographer(db: AsyncSession, *, company_id: int, removed_user_id: int) -> bool:
    """Последний Photographer удалён → Email владельцу сервиса + Owner компании (§12.4.1)."""
    left = int(
        await db.scalar(
            select(func.count())
            .select_from(CompanyMember)
            .where(
                CompanyMember.company_id == company_id,
                CompanyMember.role == "photographer",
            )
        )
        or 0
    )
    if left > 0:
        return False
    company = await db.get(Company, company_id)
    fp = f"no_photo:{company_id}"
    if await _recent_ok(db, EVENT_NO_PHOTO, fp, hours=24):
        return False
    name = company.name if company else str(company_id)
    text = (
        f"📧 Компания без Photographer\n"
        f"company_id: {company_id}\n"
        f"name: {name}\n"
        f"removed_user_id: {removed_user_id}"
    )
    dual = await alerts_svc.send_dual(
        db,
        text,
        event_type=EVENT_NO_PHOTO,
        payload={
            "fingerprint": fp,
            "company_id": company_id,
            "removed_user_id": removed_user_id,
        },
        subject=f"[3dvektor] No photographer company={company_id}",
        telegram=False,
        email=True,
    )
    owner_emailed = False
    if company:
        from app.models import User
        from app.services import email as email_svc

        owner = await db.get(User, company.owner_id)
        if owner and owner.email:
            try:
                await email_svc.send_marketing_email(
                    owner.email,
                    f"Нет активных Photographer — {name}",
                    (
                        f"В компании «{name}» (id={company_id}) не осталось сотрудников "
                        f"с ролью Photographer после удаления user_id={removed_user_id}.\n\n"
                        f"Добавьте Photographer в разделе «Команда», иначе съёмка по ссылкам "
                        f"будет недоступна сотрудникам."
                    ),
                )
                owner_emailed = True
                db.add(
                    AlertLog(
                        channel="email",
                        event_type=EVENT_NO_PHOTO,
                        payload={
                            "fingerprint": f"{fp}:owner",
                            "company_id": company_id,
                            "to": owner.email,
                            "role": "company_owner",
                        },
                        ok=True,
                        error=None,
                    )
                )
                await db.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning("no_photographer owner email: %s", exc)
    return bool(dual.get("email") or owner_emailed)


async def alert_low_balance(db: AsyncSession, company: Company, *, threshold: int | None = None) -> bool:
    """Баланс < 5000 → Email владельцу сервиса."""
    thr = threshold if threshold is not None else _low_balance_threshold()
    if company.balance >= thr:
        return False
    fp = f"low_bal:{company.id}:{company.balance // 1000}"
    if await _recent_ok(db, EVENT_LOW_BALANCE, fp, hours=24):
        return False
    text = (
        f"💰 Низкий баланс компании\n"
        f"company_id: {company.id}\n"
        f"name: {company.name}\n"
        f"balance: {company.balance} ₽\n"
        f"threshold: {thr} ₽"
    )
    dual = await alerts_svc.send_dual(
        db,
        text,
        event_type=EVENT_LOW_BALANCE,
        payload={
            "fingerprint": fp,
            "company_id": company.id,
            "balance": company.balance,
            "threshold": thr,
        },
        subject=f"[3dvektor] Low balance company={company.id}",
        telegram=False,
        email=True,
    )
    try:
        from app.services import company_notify as cn

        await cn.notify_company_event(
            db,
            company_id=company.id,
            event="low_balance",
            title="Низкий баланс компании",
            body=f"Баланс {company.balance} ₽ (порог {thr} ₽).",
            data={"company_id": str(company.id), "balance": str(company.balance), "threshold": str(thr)},
        )
    except Exception:  # noqa: BLE001
        pass
    return bool(dual.get("email"))


async def check_suspicious_orders(db: AsyncSession, *, company_id: int) -> dict[str, Any]:
    """>50 заказов за 10 минут от одной компании → Telegram + email срочный."""
    from app.services import alert_thresholds as ath

    window = int(await ath.threshold_async("company_suspicious_window_min", _suspicious_window_min()))
    thr = int(await ath.threshold_async("company_suspicious_orders_10m", _suspicious_orders()))
    since = datetime.now(timezone.utc) - timedelta(minutes=window)
    cnt = int(
        await db.scalar(
            select(func.count())
            .select_from(Order)
            .where(Order.company_id == company_id, Order.created_at >= since)
        )
        or 0
    )
    alerted = False
    if cnt >= thr:
        fp = f"susp:{company_id}:{since.replace(second=0, microsecond=0).isoformat()}"
        if not await _recent_ok(db, EVENT_SUSPICIOUS, fp, hours=1):
            company = await db.get(Company, company_id)
            text = (
                f"🚨 Подозрительная активность\n"
                f"company_id: {company_id}\n"
                f"name: {company.name if company else '—'}\n"
                f"orders: {cnt} за {window} мин (порог {thr})"
            )
            dual = await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT_SUSPICIOUS,
                payload={
                    "fingerprint": fp,
                    "company_id": company_id,
                    "count": cnt,
                    "window_min": window,
                    "threshold": thr,
                },
                subject=f"[3dvektor] Suspicious orders company={company_id}",
            )
            alerted = bool(dual.get("telegram") or dual.get("email"))
    return {"company_id": company_id, "count": cnt, "threshold": thr, "alerted": alerted}


async def scan_low_balances(db: AsyncSession) -> dict[str, Any]:
    """Celery: все компании ниже порога."""
    from app.services import alert_thresholds as ath

    thr = int(await ath.threshold_async("company_low_balance_rub", _low_balance_threshold()))
    rows = (
        await db.scalars(select(Company).where(Company.balance < thr, Company.status == "active"))
    ).all()
    sent = 0
    for c in rows:
        if await alert_low_balance(db, c, threshold=thr):
            sent += 1
    await db.commit()
    return {"checked": len(rows), "alerts_sent": sent, "threshold": thr}
