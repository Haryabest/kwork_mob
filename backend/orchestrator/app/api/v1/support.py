"""Поддержка: вопросы пользователей + треды (§20.7)."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_db_user
from app.models import SupportMessage, SupportRequest, User
from app.schemas.support import SupportQuestionRequest
from app.services.minio import minio_service

router = APIRouter()

ALLOWED_ATTACH = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_ATTACH_BYTES = 5 * 1024 * 1024
MAX_ATTACH_COUNT = 5


class SupportReply(BaseModel):
    message: str = Field(min_length=1)


def _ticket_public(req: SupportRequest, *, messages: list | None = None) -> dict:
    out = {
        "id": req.id,
        "subject": req.subject,
        "category": req.category,
        "message": req.message,
        "status": req.status,
        "attachments": list(req.attachments or []),
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }
    if messages is not None:
        out["messages"] = messages
    return out


@router.post("/questions")
async def ask_question(
    body: SupportQuestionRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    attachments = list(body.attachments or [])[:MAX_ATTACH_COUNT]
    req = SupportRequest(
        user_id=user.id,
        subject=body.subject,
        category=body.category,
        message=body.message,
        status="new",
        attachments=attachments,
    )
    db.add(req)
    await db.flush()
    db.add(SupportMessage(request_id=req.id, author_id=user.id, is_staff=False, body=body.message))
    await db.commit()
    await db.refresh(req)
    return _ticket_public(req)


@router.post("/attachments")
async def upload_support_attachment(
    file: UploadFile = File(...),
    user: User = Depends(get_current_db_user),
):
    """Загрузка скриншота/PDF до 5 МБ (§20.7.3)."""
    _ = user
    name = (file.filename or "file").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_ATTACH:
        raise HTTPException(400, "Форматы: JPG, PNG, PDF")
    data = await file.read()
    if len(data) > MAX_ATTACH_BYTES:
        raise HTTPException(400, "Файл больше 5 МБ")
    if not data:
        raise HTTPException(400, "Пустой файл")
    import uuid as uuid_lib

    key = f"support/{user.id}/{uuid_lib.uuid4().hex}{ext}"
    bucket = settings.MINIO_BUCKET_BACKUPS
    content_type = file.content_type or "application/octet-stream"
    try:
        minio_service.ensure_buckets()
        minio_service.upload_bytes(bucket, key, data, content_type=content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"Хранилище недоступно: {exc}") from exc
    url = minio_service.generate_presigned_url(bucket, key, expires=7 * 24 * 3600, method="get_object")
    return {"key": key, "url": url, "filename": file.filename, "size": len(data)}


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
    return {"items": [_ticket_public(r) for r in rows]}


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
    out = _ticket_public(
        req,
        messages=[
            {
                "id": m.id,
                "body": m.body,
                "is_staff": m.is_staff,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    )
    if user.staff_role:
        ticket_user = await db.get(User, req.user_id)
        if ticket_user:
            from sqlalchemy import func
            from app.models import Order

            orders_count = await db.scalar(
                select(func.count()).select_from(Order).where(Order.user_id == ticket_user.id)
            )
            out["user"] = {
                "id": ticket_user.id,
                "email": ticket_user.email,
                "full_name": ticket_user.full_name,
                "account_type": ticket_user.account_type,
                "status": ticket_user.status,
                "orders_count": int(orders_count or 0),
                "created_at": ticket_user.created_at.isoformat() if ticket_user.created_at else None,
            }
    return out


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
    return {"message": "ok", "status": req.status}


@router.post("/questions/{question_id}/close")
async def close_question(
    question_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    req = await db.get(SupportRequest, question_id)
    if not req or req.user_id != user.id:
        raise HTTPException(404, "Не найдено")
    req.status = "closed"
    await db.commit()
    return {"id": req.id, "status": req.status}
