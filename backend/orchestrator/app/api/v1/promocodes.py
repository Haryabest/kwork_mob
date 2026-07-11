"""Промокоды."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.schemas.promocodes import PromocodeValidateRequest

router = APIRouter()


@router.post("/validate")
async def validate_promocode(body: PromocodeValidateRequest, user: dict = Depends(get_current_user)):
    """Проверить и применить промокод к заказу."""
    raise HTTPException(501, "В разработке")


@router.get("")
async def list_promocodes(user: dict = Depends(get_current_user)):
    """Список доступных промокодов пользователя."""
    raise HTTPException(501, "В разработке")
