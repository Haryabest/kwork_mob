"""Тарифы + история цен + алерты + эскалации (admin)."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user, require_admin
from app.core.vpn import require_vpn
from app.models import AlertSettings, NsfwBlock, TaskQueue, User
from app.services import alerts as alerts_svc
from app.services import tariffs as tariff_svc


def _vpn(request: Request) -> None:
    require_vpn(request)


router = APIRouter(dependencies=[Depends(_vpn), Depends(require_admin)])


class TariffUpdate(BaseModel):
    amount_rub: int = Field(ge=1)
    note: str | None = None


class AlertSettingsBody(BaseModel):
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_enabled: bool = False
    email_enabled: bool = False
    email_to: str | None = None


class TestAlertBody(BaseModel):
    message: str = "Тестовый алерт KWork"


@router.get("/tariffs")
async def get_tariffs(db: AsyncSession = Depends(get_db)):
    return {"items": await tariff_svc.list_tariffs(db)}


@router.patch("/tariffs/{code}")
async def patch_tariff(
    code: str,
    body: TariffUpdate,
    admin: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    row = await tariff_svc.set_amount(
        db, code=code, amount_rub=body.amount_rub, changed_by=admin.id, note=body.note
    )
    await db.commit()
    return {"code": row.code, "amount_rub": row.amount_rub}


@router.get("/tariffs/history")
async def tariffs_history(code: str | None = None, db: AsyncSession = Depends(get_db)):
    return {"items": await tariff_svc.price_history(db, code=code)}


@router.get("/alerts/settings")
async def get_alert_settings(db: AsyncSession = Depends(get_db)):
    cfg = await alerts_svc.get_settings(db)
    await db.commit()
    return {
        "telegram_enabled": cfg.telegram_enabled,
        "telegram_chat_id": cfg.telegram_chat_id,
        "telegram_bot_token_set": bool(cfg.telegram_bot_token),
        "email_enabled": cfg.email_enabled,
        "email_to": cfg.email_to,
    }


@router.put("/alerts/settings")
async def put_alert_settings(body: AlertSettingsBody, db: AsyncSession = Depends(get_db)):
    cfg = await alerts_svc.get_settings(db)
    if body.telegram_bot_token is not None:
        cfg.telegram_bot_token = body.telegram_bot_token or None
    if body.telegram_chat_id is not None:
        cfg.telegram_chat_id = body.telegram_chat_id or None
    cfg.telegram_enabled = body.telegram_enabled
    cfg.email_enabled = body.email_enabled
    cfg.email_to = body.email_to
    cfg.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.post("/alerts/test")
async def test_alert(body: TestAlertBody, db: AsyncSession = Depends(get_db)):
    ok = await alerts_svc.send_telegram(db, body.message, event_type="test", payload={})
    await db.commit()
    return {"ok": ok}


@router.get("/alerts/log")
async def alert_log(db: AsyncSession = Depends(get_db)):
    return {"items": await alerts_svc.list_alert_log(db)}


@router.get("/escalations")
async def list_escalations(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(TaskQueue)
            .where(TaskQueue.escalation_count > 0)
            .order_by(TaskQueue.updated_at.desc())
            .limit(100)
        )
    ).all()
    return {
        "items": [
            {
                "task_id": r.task_id,
                "order_id": r.order_id,
                "status": r.status,
                "priority": r.priority,
                "escalation_count": r.escalation_count,
                "worker_id": r.worker_id,
                "processing_started_at": r.processing_started_at.isoformat()
                if r.processing_started_at
                else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    }


@router.get("/nsfw/sla")
async def nsfw_sla(db: AsyncSession = Depends(get_db)):
    """Очередь NSFW с дедлайном 24ч."""
    rows = (
        await db.scalars(
            select(NsfwBlock).where(NsfwBlock.verified.is_(False)).order_by(NsfwBlock.id.asc()).limit(100)
        )
    ).all()
    now = datetime.now(timezone.utc)
    items = []
    for b in rows:
        created = b.created_at or now
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        deadline = created + timedelta(hours=24)
        left = (deadline - now).total_seconds()
        items.append(
            {
                "id": b.id,
                "order_id": b.order_id,
                "user_id": b.user_id,
                "reason": b.reason,
                "refunded": b.refunded,
                "created_at": created.isoformat(),
                "deadline_at": deadline.isoformat(),
                "hours_left": round(left / 3600, 2),
                "overdue": left < 0,
            }
        )
    return {"items": items}
