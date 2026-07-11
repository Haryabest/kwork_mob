"""Маркетинговые кампании."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.security import require_admin
from app.core.vpn import require_vpn


def _vpn_guard(request: Request) -> None:
    require_vpn(request)


router = APIRouter(dependencies=[Depends(_vpn_guard), Depends(require_admin)])


@router.post("")
async def create_campaign():
    """Создать кампанию."""
    raise HTTPException(501, "В разработке")


@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: int):
    """Запустить кампанию."""
    raise HTTPException(501, "В разработке")


@router.get("/{campaign_id}/stats")
async def campaign_stats(campaign_id: int):
    """Статистика кампании (охват, конверсия, ROI)."""
    raise HTTPException(501, "В разработке")
