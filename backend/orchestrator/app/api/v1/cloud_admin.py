"""Admin API: облачные инстансы Intelion/Immers + авто-масштаб (§11.3.3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.models import PublicationBonusSettings
from app.services import cloud_autoscaling as cloud_svc
from app.services import publication as pub_svc

router = APIRouter(prefix="/cloud", tags=["Облако GPU"])


class CreateWorkersBody(BaseModel):
    provider: str = Field(pattern=r"^(intelion|immers)$")
    gpu: str = "rtx4090"
    count: int = Field(default=1, ge=1, le=10)
    image: str | None = None
    vcpus: int = Field(default=8, ge=2, le=64)
    ram_gb: int = Field(default=32, ge=8, le=512)


class AutoscalingRuleBody(BaseModel):
    id: int | None = None
    name: str
    queue_threshold: int = Field(default=20, ge=1)
    launch_count: int = Field(default=1, ge=1, le=10)
    provider: str = Field(default="intelion", pattern=r"^(intelion|immers)$")
    gpu: str = "rtx4090"
    image: str | None = None
    idle_timeout_min: int = Field(default=30, ge=5)
    max_cloud_workers: int = Field(default=5, ge=1, le=50)
    is_active: bool = True


class BonusSettingsBody(BaseModel):
    bonus_type: str = Field(pattern=r"^(discount_percent|fixed_amount|free_generation)$")
    bonus_value: int = Field(ge=0)
    promocode_ttl_days: int = Field(default=30, ge=1)
    max_uses: int = Field(default=1, ge=1)
    is_active: bool = True


@router.get("/flavors")
async def flavors(provider: str = "intelion", _: dict = Depends(require_admin)):
    return {"provider": provider, "items": await cloud_svc.list_flavors(provider)}


@router.get("/instances")
async def instances(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return {"items": await cloud_svc.list_instances(db)}


@router.post("/instances")
async def create_instances(
    body: CreateWorkersBody,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    created = await cloud_svc.create_cloud_workers(
        db,
        provider=body.provider,
        gpu=body.gpu,
        count=body.count,
        image=body.image,
        vcpus=body.vcpus,
        ram_gb=body.ram_gb,
        triggered_by="admin",
    )
    await db.commit()
    return {"created": created}


@router.post("/instances/{instance_id}/start")
async def start_instance(instance_id: str, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await cloud_svc.start_instance(db, instance_id)
    await db.commit()
    return result


@router.post("/instances/{instance_id}/stop")
async def stop_instance(instance_id: str, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await cloud_svc.stop_instance(db, instance_id)
    await db.commit()
    return result


@router.get("/autoscaling/rules")
async def list_rules(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return {"items": await cloud_svc.list_rules(db)}


@router.put("/autoscaling/rules")
async def upsert_rule(
    body: AutoscalingRuleBody,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await cloud_svc.upsert_rule(db, body.model_dump())
    await db.commit()
    return {
        "id": row.id,
        "name": row.name,
        "queue_threshold": row.queue_threshold,
        "launch_count": row.launch_count,
        "provider": row.provider,
        "gpu": row.gpu,
        "idle_timeout_min": row.idle_timeout_min,
        "max_cloud_workers": row.max_cloud_workers,
        "is_active": row.is_active,
    }


@router.post("/autoscaling/run")
async def run_autoscaling_now(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await cloud_svc.run_autoscaling_once(db)


@router.get("/costs")
async def costs(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await cloud_svc.cost_summary(db)


@router.get("/publication/bonus-settings")
async def get_bonus_settings(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    cfg = await db.get(PublicationBonusSettings, 1)
    if not cfg:
        return {"bonus_type": "discount_percent", "bonus_value": 10, "is_active": False}
    return {
        "bonus_type": cfg.bonus_type,
        "bonus_value": cfg.bonus_value,
        "promocode_ttl_days": cfg.promocode_ttl_days,
        "max_uses": cfg.max_uses,
        "is_active": cfg.is_active,
    }


@router.put("/publication/bonus-settings")
async def put_bonus_settings(
    body: BonusSettingsBody,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cfg = await db.get(PublicationBonusSettings, 1)
    if not cfg:
        cfg = PublicationBonusSettings(id=1)
        db.add(cfg)
    cfg.bonus_type = body.bonus_type
    cfg.bonus_value = body.bonus_value
    cfg.promocode_ttl_days = body.promocode_ttl_days
    cfg.max_uses = body.max_uses
    cfg.is_active = body.is_active
    await db.commit()
    return {"ok": True}


@router.post("/publication/links/{link_id}/force-verify")
async def force_verify_link(link_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    from app.models import Model3D, ModelPublicationLink

    link = await db.get(ModelPublicationLink, link_id)
    if not link:
        from fastapi import HTTPException

        raise HTTPException(404, "Ссылка не найдена")
    model = await db.scalar(select(Model3D).where(Model3D.uuid == link.model_uuid))
    if not model:
        from fastapi import HTTPException

        raise HTTPException(404, "Модель не найдена")
    link, plain = await pub_svc.force_verify(db, link=link, model=model)
    await db.commit()
    return {"id": link.id, "status": link.status, "promocode": plain}
