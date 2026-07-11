"""Поддержка: вопросы пользователей."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user
from app.models import SupportMessage, SupportRequest, User
from app.schemas.support import SupportQuestionRequest

router = APIRouter()


class SupportReply(BaseModel):
    message: str = Field(min_length=1)


@router.post("/questions")
async def ask_question(
    body: SupportQuestionRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    req = SupportRequest(
        user_id=user.id,
        subject=body.subject,
        category=body.category,
        message=body.message,
        status="new",
    )
    db.add(req)
    await db.flush()
    db.add(SupportMessage(request_id=req.id, author_id=user.id, is_staff=False, body=body.message))
    await db.commit()
    await db.refresh(req)
    return {"id": req.id, "status": req.status}


@router.get("/questions")
async def list_questions(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(
            select(SupportRequest).where(SupportRequest.user_id == user.id).order_by(SupportRequest.id.desc())
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "subject": r.subject,
                "category": r.category,
                "message": r.message,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/questions/{question_id}")
async def get_question(
    question_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    req = await db.get(SupportRequest, question_id)
    if not req or (req.user_id != user.id and not user.staff_role):
        raise HTTPException(404, "Не найдено")
    messages = (
        await db.scalars(
            select(SupportMessage).where(SupportMessage.request_id == question_id).order_by(SupportMessage.id)
        )
    ).all()
    return {
        "id": req.id,
        "subject": req.subject,
        "category": req.category,
        "status": req.status,
        "messages": [
            {
                "id": m.id,
                "body": m.body,
                "is_staff": m.is_staff,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.post("/questions/{question_id}/messages")
async def reply_question(
    question_id: int,
    body: SupportReply,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Дополнение пользователя к своему обращению."""
    req = await db.get(SupportRequest, question_id)
    if not req or req.user_id != user.id:
        raise HTTPException(404, "Не найдено")
    if req.status in ("closed", "resolved"):
        raise HTTPException(400, "Обращение закрыто")
    db.add(SupportMessage(request_id=req.id, author_id=user.id, is_staff=False, body=body.message))
    if req.status == "answered":
        req.status = "waiting_user"
    await db.commit()
    return {"message": "ok"}
