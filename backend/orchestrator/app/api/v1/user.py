"""Пользователь: профиль, баланс, транзакции, модели."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user
from app.models import Model3D, Transaction, User
from app.schemas.auth import AccountTypeRequest
from app.services import auth as auth_service

router = APIRouter()


class TopupRequest(BaseModel):
    amount: int = Field(default=1000, ge=100, le=500_000)


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "account_type": user.account_type,
        "status": user.status,
        "email_verified": user.email_verified,
        "staff_role": user.staff_role,
        "role": user.staff_role or "user",
        "balance": user.balance,
        "marketing_opt_in": user.marketing_opt_in,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_db_user)):
    """Текущий пользователь (для seller и staff)."""
    return _user_payload(user)


@router.patch("/me")
async def update_me(
    payload: dict,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновление профиля (ФИО, телефон, маркетинг)."""
    if "full_name" in payload:
        user.full_name = payload["full_name"]
    if "phone" in payload:
        user.phone = payload["phone"]
    if "marketing_opt_in" in payload:
        user.marketing_opt_in = bool(payload["marketing_opt_in"])
    await db.commit()
    await db.refresh(user)
    return _user_payload(user)


@router.post("/account-type")
async def account_type(
    body: AccountTypeRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await auth_service.set_account_type(db, user, body)
    return {"message": "ok", "status": updated.status, "account_type": updated.account_type}


@router.get("/balance")
async def get_balance(user: User = Depends(get_current_db_user)):
    return {"balance": user.balance, "currency": "RUB"}


@router.get("/transactions")
async def get_transactions(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(
            select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.id.desc()).limit(100)
        )
    ).all()
    return {
        "items": [
            {
                "id": t.id,
                "amount": t.amount,
                "type": t.tx_type,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ]
    }


@router.post("/balance/topup")
async def topup_balance(
    body: TopupRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Пополнение баланса через ЮKassa (mock без ключей)."""
    from app.core.config import settings
    from app.services.yookassa import yookassa_service

    amount = body.amount
    payment = await yookassa_service.create_payment(
        amount,
        f"Пополнение баланса KWork Mob ({user.email})",
        return_url=f"{settings.API_BASE_URL.replace(':8000', ':3000')}/balance",
        metadata={"user_id": str(user.id), "amount": str(amount)},
    )

    if payment.get("mock"):
        user.balance += amount
        db.add(
            Transaction(
                user_id=user.id,
                amount=amount,
                tx_type="topup",
                description="Пополнение (mock ЮKassa)",
                external_id=payment["id"],
            )
        )
        await db.commit()
        payment["status"] = "succeeded"
        payment["balance"] = user.balance

    return payment


@router.get("/models")
async def list_user_models(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(select(Model3D).where(Model3D.user_id == user.id).order_by(Model3D.id.desc()).limit(100))
    ).all()
    return {
        "items": [
            {
                "uuid": m.uuid,
                "order_id": m.order_id,
                "glb_url": m.glb_url,
                "usdz_url": m.usdz_url,
                "publish_status": m.publish_status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in rows
        ]
    }
