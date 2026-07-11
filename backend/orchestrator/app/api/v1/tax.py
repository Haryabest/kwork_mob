"""Налоговый модуль: счета, акты, выгрузки."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user

router = APIRouter()


@router.post("/invoice/{order_id}")
async def generate_invoice(order_id: int, user: dict = Depends(get_current_user)):
    """Сформировать счёт на оплату (PDF)."""
    raise HTTPException(501, "В разработке")


@router.post("/act/{order_id}")
async def generate_act(order_id: int, user: dict = Depends(get_current_user)):
    """Сформировать акт выполненных услуг (PDF)."""
    raise HTTPException(501, "В разработке")


@router.get("/transactions/export")
async def export_transactions(user: dict = Depends(get_current_user)):
    """Выгрузить операции за период (Excel/PDF)."""
    raise HTTPException(501, "В разработке")
