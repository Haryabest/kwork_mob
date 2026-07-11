"""FAQ (публичный + admin)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_staff
from app.models import FaqItem

router = APIRouter()


class FaqCreate(BaseModel):
    category: str = "Общее"
    question: str = Field(min_length=3)
    answer: str = Field(min_length=3)
    is_published: bool = True


@router.get("")
async def get_faq(db: AsyncSession = Depends(get_db)):
    """Список опубликованных FAQ."""
    rows = (
        await db.scalars(select(FaqItem).where(FaqItem.is_published.is_(True)).order_by(FaqItem.id))
    ).all()
    return {
        "items": [
            {
                "id": f.id,
                "category": f.category,
                "question": f.question,
                "answer": f.answer,
                "version": f.version,
            }
            for f in rows
        ]
    }


@router.get("/all")
async def get_faq_all(_: dict = Depends(require_staff), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(FaqItem).order_by(FaqItem.id))).all()
    return {
        "items": [
            {
                "id": f.id,
                "category": f.category,
                "question": f.question,
                "answer": f.answer,
                "version": f.version,
                "is_published": f.is_published,
            }
            for f in rows
        ]
    }


@router.post("")
async def create_faq(
    body: FaqCreate,
    _: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    item = FaqItem(
        category=body.category,
        question=body.question,
        answer=body.answer,
        is_published=body.is_published,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": item.id, "message": "Создано"}


@router.patch("/{faq_id}")
async def update_faq(
    faq_id: int,
    body: FaqCreate,
    _: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(FaqItem, faq_id)
    if not item:
        raise HTTPException(404, "Не найдено")
    item.category = body.category
    item.question = body.question
    item.answer = body.answer
    item.is_published = body.is_published
    item.version += 1
    await db.commit()
    return {"id": item.id, "version": item.version}
