"""Алерты владельцу: Telegram (+ лог) §11 / §13."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.models import AlertLog, AlertSettings

logger = logging.getLogger(__name__)


async def get_settings(db: AsyncSession) -> AlertSettings:
    row = await db.get(AlertSettings, 1)
    if not row:
        row = AlertSettings(id=1, telegram_enabled=False)
        db.add(row)
        await db.flush()
    # env override если в БД пусто
    if not row.telegram_bot_token and settings.TELEGRAM_BOT_TOKEN:
        row.telegram_bot_token = settings.TELEGRAM_BOT_TOKEN
    if not row.telegram_chat_id and settings.TELEGRAM_CHAT_ID:
        row.telegram_chat_id = settings.TELEGRAM_CHAT_ID
    return row


async def send_telegram(db: AsyncSession, text: str, *, event_type: str, payload: dict | None = None) -> bool:
    cfg = await get_settings(db)
    token = cfg.telegram_bot_token or settings.TELEGRAM_BOT_TOKEN
    chat = cfg.telegram_chat_id or settings.TELEGRAM_CHAT_ID
    enabled = cfg.telegram_enabled or bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)
    if not enabled or not token or not chat:
        db.add(
            AlertLog(
                channel="telegram",
                event_type=event_type,
                payload=payload or {"text": text},
                ok=False,
                error="telegram not configured",
            )
        )
        await db.flush()
        return False

    ok = False
    err: str | None = None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat, "text": text[:4000], "disable_web_page_preview": True},
            )
            if resp.status_code >= 400:
                err = resp.text[:500]
            else:
                ok = True
    except Exception as exc:  # noqa: BLE001
        err = str(exc)[:500]
        logger.warning("Telegram alert failed: %s", exc)

    db.add(
        AlertLog(
            channel="telegram",
            event_type=event_type,
            payload={**(payload or {}), "text": text},
            ok=ok,
            error=err,
        )
    )
    await db.flush()
    return ok


async def notify_escalation(
    *,
    task_id: str,
    stage: str,
    escalation_count: int,
    order_id: int | None = None,
    duration_min: int | None = None,
    refunded: bool = False,
) -> None:
    text = (
        f"⚠️ Эскалация задачи\n"
        f"task: {task_id}\n"
        f"stage: {stage}\n"
        f"count: {escalation_count}\n"
        f"order: {order_id or '—'}\n"
        f"duration_min: {duration_min or '—'}\n"
        f"refunded: {refunded}"
    )
    async with async_session() as db:
        await send_telegram(
            db,
            text,
            event_type="task_escalated",
            payload={
                "task_id": task_id,
                "stage": stage,
                "escalation_count": escalation_count,
                "order_id": order_id,
                "duration_min": duration_min,
                "refunded": refunded,
            },
        )
        await db.commit()


async def notify_nsfw_block(*, order_id: int, user_id: int, confidence: float) -> None:
    text = f"🛡 NSFW блок\norder #{order_id}\nuser {user_id}\nconfidence {confidence:.2f}\nПроверка в течение 24ч"
    async with async_session() as db:
        await send_telegram(
            db,
            text,
            event_type="nsfw_blocked",
            payload={"order_id": order_id, "user_id": user_id, "confidence": confidence},
        )
        await db.commit()


async def list_alert_log(db: AsyncSession, limit: int = 100) -> list[dict[str, Any]]:
    rows = (await db.scalars(select(AlertLog).order_by(AlertLog.id.desc()).limit(limit))).all()
    return [
        {
            "id": r.id,
            "channel": r.channel,
            "event_type": r.event_type,
            "payload": r.payload,
            "ok": r.ok,
            "error": r.error,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
