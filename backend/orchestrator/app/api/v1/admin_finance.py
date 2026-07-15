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
    amount_rub: int = Field(ge=0)
    note: str | None = None


class AlertSettingsBody(BaseModel):
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_enabled: bool = False
    email_enabled: bool = False
    email_to: str | None = None
    email_recipients: list[str] | None = None  # до 5 §12.4.2
    thresholds: dict | None = None


class TestAlertBody(BaseModel):
    message: str = "Тестовый алерт KWork"
    channel: str = "dual"  # telegram | email | dual


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
    from app.services import alert_thresholds as ath
    from app.services.alerts import _email_recipients

    cfg = await alerts_svc.get_settings(db)
    thresholds = await ath.load_thresholds(db)
    recipients = _email_recipients(cfg)
    await db.commit()
    return {
        "telegram_enabled": cfg.telegram_enabled,
        "telegram_chat_id": cfg.telegram_chat_id,
        "telegram_bot_token_set": bool(cfg.telegram_bot_token),
        "email_enabled": cfg.email_enabled,
        "email_to": cfg.email_to,
        "email_recipients": recipients,
        "email_recipients_max": 5,
        "thresholds": thresholds,
        "threshold_keys": list(ath.THRESHOLD_KEYS.keys()),
    }


@router.put("/alerts/settings")
async def put_alert_settings(body: AlertSettingsBody, db: AsyncSession = Depends(get_db)):
    from app.services import alert_thresholds as ath
    from app.services.alerts import normalize_email_recipients

    cfg = await alerts_svc.get_settings(db)
    if body.telegram_bot_token is not None:
        cfg.telegram_bot_token = body.telegram_bot_token or None
    if body.telegram_chat_id is not None:
        cfg.telegram_chat_id = body.telegram_chat_id or None
    cfg.telegram_enabled = body.telegram_enabled
    cfg.email_enabled = body.email_enabled
    csv, recipients = normalize_email_recipients(body.email_recipients, body.email_to)
    cfg.email_to = csv
    # дублируем список в thresholds для явного UI round-trip
    thr_map = dict(cfg.thresholds or {})
    thr_map["email_recipients"] = recipients
    cfg.thresholds = thr_map
    cfg.updated_at = datetime.now(timezone.utc)
    thresholds = None
    if body.thresholds is not None:
        # не затирать email_recipients из thresholds patch
        patch = dict(body.thresholds)
        patch.pop("email_recipients", None)
        thresholds = await ath.save_thresholds(db, patch)
        cfg.thresholds = {**(cfg.thresholds or {}), "email_recipients": recipients}
    else:
        thresholds = await ath.load_thresholds(db)
    await db.commit()
    return {"ok": True, "thresholds": thresholds, "email_recipients": recipients}


@router.post("/alerts/test")
async def test_alert(body: TestAlertBody, db: AsyncSession = Depends(get_db)):
    channel = (body.channel or "dual").lower()
    result = {"telegram": False, "email": False}
    if channel in ("telegram", "dual"):
        result["telegram"] = await alerts_svc.send_telegram(
            db, body.message, event_type="test", payload={}
        )
    if channel in ("email", "dual"):
        result["email"] = await alerts_svc.send_email_alert(
            db, body.message, event_type="test", subject="[3dvektor] Test alert", payload={}
        )
    await db.commit()
    return {"ok": result["telegram"] or result["email"], **result}


@router.get("/task-conflicts")
async def list_task_conflicts(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Журнал Redlock / duplicate completion (§12.4.1 / §13.3.5)."""
    from app.models import TaskConflict

    rows = (
        await db.scalars(
            select(TaskConflict).order_by(TaskConflict.id.desc()).limit(min(limit, 500))
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "worker_id": r.worker_id,
                "reason": r.reason,
                "details": r.details or {},
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/alerts/log")
async def alert_log(
    event_type: str | None = None,
    channel: str | None = None,
    ok: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """История alert_log §12.4.3."""
    return await alerts_svc.list_alert_log(
        db,
        limit=limit,
        offset=offset,
        event_type=event_type,
        channel=channel,
        ok=ok,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/alerts/log/export")
async def alert_log_export(
    event_type: str | None = None,
    channel: str | None = None,
    ok: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    data = await alerts_svc.list_alert_log(
        db,
        limit=5000,
        offset=0,
        event_type=event_type,
        channel=channel,
        ok=ok,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=alerts_svc.alert_log_to_csv(data["items"]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="alert-log.csv"'},
    )


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
