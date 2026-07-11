"""Публичные эндпоинты съёмки по ссылке."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/shoot", tags=["Съёмка по ссылке"])


@router.get("/{token}")
async def get_shoot_data(token: str):
    """Данные для съёмки (перенаправление на приложение)."""
    raise HTTPException(501, "В разработке")


@router.post("/{token}/upload")
async def upload_by_link(token: str):
    """Загрузка готовых 12 фото по ссылке (без AR-съёмки)."""
    raise HTTPException(501, "В разработке")
