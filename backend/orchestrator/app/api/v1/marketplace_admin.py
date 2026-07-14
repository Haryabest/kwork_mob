"""Admin: credentials WB/Ozon (§7.6 / §14.6)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_admin
from app.core.vpn import require_vpn
from app.models import MarketplaceCredential
from app.services import marketplace_upload as mp_svc


def _vpn(request: Request) -> None:
    require_vpn(request)


router = APIRouter(
    prefix="/admin/marketplace",
    tags=["Marketplace API"],
    dependencies=[Depends(_vpn), Depends(require_admin)],
)


class CredentialBody(BaseModel):
    marketplace: str = Field(pattern=r"^(wb|ozon|wildberries)$")
    api_key: str = Field(min_length=8, max_length=512)
    client_id: str | None = Field(default=None, max_length=64)
    company_id: int | None = None
    enabled: bool = True


class CredentialToggleBody(BaseModel):
    enabled: bool


@router.get("/status")
async def marketplace_status():
    return {
        "upload_enabled": settings.MARKETPLACE_UPLOAD_ENABLED,
        "max_retries": settings.MARKETPLACE_UPLOAD_MAX_RETRIES,
        "wb_base": settings.WB_API_BASE_URL,
        "ozon_base": settings.OZON_API_BASE_URL,
    }


@router.get("/credentials")
async def list_credentials(
    company_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(MarketplaceCredential).order_by(MarketplaceCredential.id)
    if company_id is not None:
        q = q.where(MarketplaceCredential.company_id == company_id)
    rows = (await db.scalars(q)).all()
    return {"items": [mp_svc.credential_public(r) for r in rows]}


@router.put("/credentials")
async def upsert_credentials(body: CredentialBody, db: AsyncSession = Depends(get_db)):
    row = await mp_svc.upsert_credential(
        db,
        marketplace=body.marketplace,
        api_key=body.api_key,
        company_id=body.company_id,
        client_id=body.client_id,
        enabled=body.enabled,
    )
    await db.commit()
    return mp_svc.credential_public(row)


@router.patch("/credentials/{cred_id}")
async def toggle_credential(
    cred_id: int,
    body: CredentialToggleBody,
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(MarketplaceCredential, cred_id)
    if not row:
        raise HTTPException(404, "Credential не найден")
    row.enabled = body.enabled
    await db.commit()
    return mp_svc.credential_public(row)


@router.get("/upload-logs")
async def upload_logs(
    model_uuid: str | None = Query(None),
    company_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items = await mp_svc.list_upload_logs(db, model_uuid=model_uuid, company_id=company_id)
    return {"items": items}
