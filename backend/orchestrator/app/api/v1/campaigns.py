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
