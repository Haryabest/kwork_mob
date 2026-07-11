"""3D-модели: скачивание, публикация, оценка, импорт."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.schemas.models import ModelRateRequest

router = APIRouter()


@router.get("/{model_uuid}/download")
async def download_model(model_uuid: str, user: dict = Depends(get_current_user)):
    """Presigned URL для скачивания .glb из MinIO."""
    raise HTTPException(501, "В разработке")


@router.post("/{model_uuid}/publish/mark")
async def mark_published(model_uuid: str, user: dict = Depends(get_current_user)):
    """Отметка «Я опубликовал»."""
    raise HTTPException(501, "В разработке")


@router.post("/{model_uuid}/rate")
async def rate_model(model_uuid: str, body: ModelRateRequest, user: dict = Depends(get_current_user)):
    """Оценка качества модели (1–5 + причины)."""
    raise HTTPException(501, "В разработке")


@router.post("/import")
async def import_model(user: dict = Depends(get_current_user)):
    """Импорт готовой модели (только Owner)."""
    raise HTTPException(501, "В разработке")
