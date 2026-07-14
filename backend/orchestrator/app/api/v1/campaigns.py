"""Маркетинговые кампании + push (§11.7–11.8)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user, require_admin
from app.core.vpn import require_vpn
from app.models import Campaign, User
from app.services import campaigns as camp_svc


def _vpn(request: Request) -> None:
    require_vpn(request)


router = APIRouter(dependencies=[Depends(_vpn), Depends(require_admin)])


class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    template: str
    segment: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)
    budget_rub: int | None = Field(default=None, ge=0)


class PushCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    segment: dict = Field(default_factory=dict)


class PushTestBody(BaseModel):
    user_id: int | None = None
    title: str = Field(default="KWork Mob test", max_length=255)
    body: str = Field(default="Push E2E OK", min_length=1)


@router.get("/templates")
async def templates():
    return {"items": [{"code": k, "title": v} for k, v in camp_svc.TEMPLATES.items()]}


@router.get("")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Campaign).order_by(Campaign.id.desc()).limit(100))).all()
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "template": c.template,
                "status": c.status,
                "stats": c.stats,
                "budget_rub": c.budget_rub,
                "started_at": c.started_at.isoformat() if c.started_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in rows
        ]
    }


@router.post("")
async def create_campaign(
    body: CampaignCreate,
    admin: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    row = await camp_svc.create_campaign(
        db,
        name=body.name,
        template=body.template,
        segment=body.segment,
        config=body.config,
        budget_rub=body.budget_rub,
        created_by=admin.id,
    )
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "status": row.status, "name": row.name}


@router.post("/push")
async def create_push(
    body: PushCreate,
    admin: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    row = await camp_svc.send_push_broadcast(
        db,
        title=body.title,
        body=body.body,
        segment=body.segment,
        created_by=admin.id,
    )
    await db.commit()
    return {"id": row.id, "status": row.status, "stats": row.stats}


@router.post("/push/test")
async def push_e2e_test(
    body: PushTestBody,
    admin: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """E2E проверка FCM (§3.4.3)."""
    from app.services import push as push_svc

    uid = body.user_id or admin.id
    result = await push_svc.send_to_user(db, uid, body.title, body.body, email_fallback=True)
    await db.commit()
    return result


@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    row = await camp_svc.start_campaign(db, campaign_id)
    await db.commit()
    return {"id": row.id, "status": row.status, "stats": row.stats}


@router.post("/{campaign_id}/stop")
async def stop_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timezone

    row = await db.get(Campaign, campaign_id)
    if not row:
        raise HTTPException(404, "Не найдена")
    row.status = "stopped"
    row.stopped_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": row.id, "status": row.status}


@router.get("/{campaign_id}/stats")
async def campaign_stats(campaign_id: int, db: AsyncSession = Depends(get_db)):
    stats = await camp_svc.campaign_stats(db, campaign_id)
    await db.commit()
    return stats


# Публичный трекинг кликов (без VPN) §11.7
public_router = APIRouter(tags=["Campaign track"])


@public_router.get("/{campaign_id}/click")
async def campaign_click(
    campaign_id: int,
    request: Request,
    u: str | None = None,
    v: str | None = None,
    uid: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Редирект с учётом клика (A/B)."""
    from fastapi.responses import RedirectResponse

    ip = request.client.host if request.client else None
    result = await camp_svc.track_click(
        db,
        campaign_id=campaign_id,
        user_id=uid,
        variant=v,
        target_url=u,
        ip=ip,
    )
    await db.commit()
    return RedirectResponse(url=result["redirect"], status_code=302)