"""Алерты владельцу: Telegram + email (§11 / §12.4 / §13)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import func, select
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
    if not row.telegram_bot_token and settings.TELEGRAM_BOT_TOKEN:
        row.telegram_bot_token = settings.TELEGRAM_BOT_TOKEN
    if not row.telegram_chat_id and settings.TELEGRAM_CHAT_ID:
        row.telegram_chat_id = settings.TELEGRAM_CHAT_ID
    return row


def _email_recipients(cfg: AlertSettings) -> list[str]:
    """До 5 адресов §12.4.2 (comma/semicolon/`email_recipients` JSON)."""
    extras: list[str] = []
    thr = cfg.thresholds if isinstance(cfg.thresholds, dict) else {}
    raw_list = thr.get("email_recipients")
    if isinstance(raw_list, list):
        extras = [str(x).strip() for x in raw_list if str(x).strip()]
    raw = (cfg.email_to or "").strip()
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()] if raw else []
    seen: set[str] = set()
    out: list[str] = []
    for p in extras + parts:
        key = p.lower()
        if key in seen:
            continue
        if "@" not in p:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= 5:
            break
    return out


def normalize_email_recipients(emails: list[str] | None, email_to: str | None = None) -> tuple[str | None, list[str]]:
    """Возвращает (email_to csv, list≤5) для сохранения."""
    parts: list[str] = []
    if emails:
        parts.extend(str(x).strip() for x in emails if str(x).strip())
    if email_to:
        parts.extend(p.strip() for p in email_to.replace(";", ",").split(",") if p.strip())
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        key = p.lower()
        if key in seen or "@" not in p:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= 5:
            break
    csv = ", ".join(out) if out else None
    return csv, out


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


async def send_email_alert(
    db: AsyncSession,
    text: str,
    *,
    event_type: str,
    subject: str | None = None,
    payload: dict | None = None,
) -> bool:
    """Email-канал алертов (§12.4.2) — до 5 адресов."""
    from app.services import email as email_svc

    cfg = await get_settings(db)
    recipients = _email_recipients(cfg) if cfg.email_enabled else []
    if not cfg.email_enabled or not recipients:
        db.add(
            AlertLog(
                channel="email",
                event_type=event_type,
                payload=payload or {"text": text},
                ok=False,
                error="email not configured",
            )
        )
        await db.flush()
        return False

    subj = subject or f"[3dvektor] {event_type}"
    ok_any = False
    for to in recipients:
        try:
            await email_svc.send_alert_email(to, subj, text)
            ok_any = True
            db.add(
                AlertLog(
                    channel="email",
                    event_type=event_type,
                    payload={**(payload or {}), "text": text, "to": to},
                    ok=True,
                    error=None,
                )
            )
        except Exception as exc:  # noqa: BLE001
            err = str(exc)[:500]
            logger.warning("Email alert failed → %s: %s", to, exc)
            db.add(
                AlertLog(
                    channel="email",
                    event_type=event_type,
                    payload={**(payload or {}), "text": text, "to": to},
                    ok=False,
                    error=err,
                )
            )
    await db.flush()
    return ok_any


async def send_dual(
    db: AsyncSession,
    text: str,
    *,
    event_type: str,
    payload: dict | None = None,
    subject: str | None = None,
    telegram: bool = True,
    email: bool = True,
) -> dict[str, bool]:
    """Telegram + email по §12.4."""
    result = {"telegram": False, "email": False}
    if telegram:
        result["telegram"] = await send_telegram(db, text, event_type=event_type, payload=payload)
    if email:
        result["email"] = await send_email_alert(
            db, text, event_type=event_type, subject=subject, payload=payload
        )
    return result


async def notify_escalation(
    *,
    task_id: str,
    stage: str,
    escalation_count: int,
    order_id: int | None = None,
    duration_min: int | None = None,
    refunded: bool = False,
) -> None:
    """Task эскалация → Telegram + email (§12.4 dual-channel)."""
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
        await send_dual(
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
            subject="[3dvektor] Task escalation",
            telegram=True,
            email=True,
        )
        await db.commit()


async def notify_nsfw_block(*, order_id: int, user_id: int, confidence: float) -> None:
    text = f"🛡 NSFW блок\norder #{order_id}\nuser {user_id}\nconf {confidence:.2f}\nПроверка в течение 24ч"
    async with async_session() as db:
        await send_dual(
            db,
            text,
            event_type="nsfw_blocked",
            payload={"order_id": order_id, "user_id": user_id, "confidence": confidence},
            subject="[3dvektor] NSFW block",
        )
        await db.commit()


async def notify_gpu_thermal(
    *,
    worker_id: str,
    temp_c: float,
    task_id: str | None = None,
) -> None:
    """GPU >85°C → Telegram (срочный) + email (§12.4.1 / §13.4)."""
    threshold = getattr(settings, "GPU_TEMP_ALERT_C", 85)
    text = (
        f"🚨 GPU температура\n"
        f"worker: {worker_id}\n"
        f"temp: {temp_c}°C\n"
        f"task: {task_id or '—'}\n"
        f"порог: {threshold}°C"
    )
    async with async_session() as db:
        await send_dual(
            db,
            text,
            event_type="gpu_thermal",
            payload={"worker_id": worker_id, "temp_c": temp_c, "task_id": task_id},
            subject=f"[3dvektor] GPU {temp_c}°C — {worker_id}",
        )
        await db.commit()


async def list_alert_log(
    db: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
    event_type: str | None = None,
    channel: str | None = None,
    ok: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    """История алертов §12.4.3 — фильтр по типу, каналу, статусу, дате."""
    q = select(AlertLog)
    count_q = select(func.count()).select_from(AlertLog)
    if event_type:
        q = q.where(AlertLog.event_type == event_type)
        count_q = count_q.where(AlertLog.event_type == event_type)
    if channel:
        q = q.where(AlertLog.channel == channel)
        count_q = count_q.where(AlertLog.channel == channel)
    if ok is not None:
        q = q.where(AlertLog.ok.is_(ok))
        count_q = count_q.where(AlertLog.ok.is_(ok))
    if date_from:
        q = q.where(AlertLog.created_at >= date_from)
        count_q = count_q.where(AlertLog.created_at >= date_from)
    if date_to:
        q = q.where(AlertLog.created_at <= date_to)
        count_q = count_q.where(AlertLog.created_at <= date_to)

    total = int(await db.scalar(count_q) or 0)
    rows = (
        await db.scalars(q.order_by(AlertLog.id.desc()).offset(offset).limit(min(limit, 2000)))
    ).all()

    def _row(r: AlertLog) -> dict[str, Any]:
        payload = r.payload or {}
        text = payload.get("text") or payload.get("message") or ""
        return {
            "id": r.id,
            "channel": r.channel,
            "event_type": r.event_type,
            "payload": payload,
            "text": str(text)[:500] if text else None,
            "company_id": payload.get("company_id"),
            "worker_id": payload.get("worker_id"),
            "ok": r.ok,
            "error": r.error,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    return {"items": [_row(r) for r in rows], "total": total}


def alert_log_to_csv(items: list[dict[str, Any]]) -> str:
    import csv
    import io
    import json

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "id",
            "created_at",
            "event_type",
            "channel",
            "ok",
            "company_id",
            "worker_id",
            "text",
            "error",
            "payload_json",
        ]
    )
    for it in items:
        w.writerow(
            [
                it.get("id"),
                it.get("created_at"),
                it.get("event_type"),
                it.get("channel"),
                it.get("ok"),
                it.get("company_id"),
                it.get("worker_id"),
                (it.get("text") or "").replace("\n", " ")[:500],
                it.get("error") or "",
                json.dumps(it.get("payload") or {}, ensure_ascii=False)[:2000],
            ]
        )
    return buf.getvalue()
