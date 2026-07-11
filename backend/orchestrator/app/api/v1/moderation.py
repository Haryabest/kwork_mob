"""Модерация NSFW."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.security import require_admin
from app.core.vpn import require_vpn


def _vpn_guard(request: Request) -> None:
    require_vpn(request)


router = APIRouter(dependencies=[Depends(_vpn_guard), Depends(require_admin)])


@router.post("/block")
async def manual_block():
    """Ручная блокировка модели."""
    raise HTTPException(501, "В разработке")


@router.get("/reports")
async def nsfw_reports():
    """Список заблокированных NSFW-заказов."""
    raise HTTPException(501, "В разработке")


@router.post("/{block_id}/verify")
async def verify_nsfw(block_id: int):
    """Ручная верификация (разблокировка / постоянная блокировка)."""
    raise HTTPException(501, "В разработке")
