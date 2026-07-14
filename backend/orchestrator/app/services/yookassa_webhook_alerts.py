"""YooKassa inbound webhook fail streak ≥5 для order → alert (§8.1 / §14.1)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.database import async_session
from app.core.redis import get_redis
from app.models import AuditLog, Order
from app.services import alerts as alerts_svc

logger = logging.getLogger(__name__)

EVENT = "yookassa_webhook_failures"


def _threshold() -> int:
    return int(getattr(settings, "YOOKASSA_WEBHOOK_FAIL_STREAK", 5) or 5)


def _redis_key(order_id: int | str) -> str:
    return f"yookassa:webhook_fail:{order_id}"


async def record_webhook_success(order_id: int | str | None) -> None:
    if order_id is None:
        return
    try:
        redis = await get_redis()
        await redis.delete(_redis_key(order_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("yk webhook streak reset: %s", exc)


async def record_webhook_failure(
    *,
    order_id: int | str | None,
    payment_id: str | None = None,
    detail: str = "",
) -> dict[str, Any]:
    """Инкремент fail streak; при ≥5 — dual alert + audit (ручная проверка §8.1)."""
    if order_id is None:
        order_id = payment_id or "unknown"
    streak = 0
    try:
        redis = await get_redis()
        streak = int(await redis.incr(_redis_key(order_id)))
        await redis.expire(_redis_key(order_id), 86400 * 3)
    except Exception as exc:  # noqa: BLE001
        logger.warning("yk webhook streak incr: %s", exc)
        return {"streak": 0, "alerted": False}

    thr = _threshold()
    alerted = False
    if streak < thr:
        return {"streak": streak, "threshold": thr, "alerted": False}

    text = (
        f"🚨 ЮKassa webhook fails ≥{thr} подряд\n"
        f"order_id: {order_id}\n"
        f"payment_id: {payment_id or '—'}\n"
        f"streak: {streak}\n"
        f"detail: {(detail or '')[:300]}"
    )
    ticket: dict[str, Any] = {"created": False}
    try:
        async with async_session() as db:
            dual = await alerts_svc.send_dual(
                db,
                text,
                event_type=EVENT,
                payload={
                    "fingerprint": f"yk_wh:{order_id}:{streak // thr}",
                    "order_id": str(order_id),
                    "payment_id": payment_id,
                    "streak": streak,
                },
                subject=f"[3dvektor] YooKassa webhook fails order={order_id}",
            )
            user_id = None
            company_id = None
            try:
                oid = int(order_id)
                order = await db.get(Order, oid)
                if order:
                    user_id = order.user_id
                    company_id = order.company_id
            except (TypeError, ValueError):
                pass
            db.add(
                AuditLog(
                    company_id=company_id,
                    user_id=user_id,
                    action="yookassa_webhook_manual_review",
                    details={
                        "order_id": str(order_id),
                        "payment_id": payment_id,
                        "streak": streak,
                        "detail": (detail or "")[:500],
                    },
                )
            )
            try:
                from app.services import support_tickets as st

                ticket = await st.create_manual_review_ticket(
                    db,
                    order_id=order_id,
                    payment_id=payment_id,
                    streak=streak,
                    detail=detail,
                    user_id=user_id,
                    company_id=company_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("manual_review ticket: %s", exc)
                ticket = {"created": False, "error": str(exc)[:200]}
            await db.commit()
            alerted = bool(dual.get("telegram") or dual.get("email"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("yk webhook alert: %s", exc)
    return {"streak": streak, "threshold": thr, "alerted": alerted, "ticket": ticket}
