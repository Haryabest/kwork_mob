"""Администрирование: B2B, воркеры, пользователи, поддержка."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user, require_admin, require_staff
from app.core.vpn import require_vpn
from app.models import (
    Company,
    CompanyMember,
    Order,
    SupportMessage,
    SupportRequest,
    TaskQueue,
    User,
    UserConsent,
    WorkerNode,
)
from app.schemas.support import SupportQuestionRequest
from app.services.queue import queue_service


def _vpn_guard(request: Request) -> None:
    require_vpn(request)


router = APIRouter(dependencies=[Depends(_vpn_guard)])


class WorkerUpsert(BaseModel):
    status: str = "online"
    gpu_name: str | None = None
    gpu_load: float | None = None
    weight: float = Field(default=0, ge=-1, le=1)


class GracePeriodBody(BaseModel):
    grace_period: int = Field(ge=25, le=30)


class BlockUserBody(BaseModel):
    blocked: bool = True


@router.get("/companies")
async def list_companies(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Company).order_by(Company.id.desc()))).all()
    items = []
    for c in rows:
        members = await db.scalar(
            select(func.count()).select_from(CompanyMember).where(CompanyMember.company_id == c.id)
        )
        items.append(
            {
                "id": c.id,
                "name": c.name,
                "inn": c.inn,
                "balance": c.balance,
                "status": c.status,
                "members_count": int(members or 0),
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
        )
    return {"items": items}


@router.get("/companies/{company_id}")
async def get_company(company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    members = (
        await db.scalars(select(CompanyMember).where(CompanyMember.company_id == company_id))
    ).all()
    return {
        "id": company.id,
        "name": company.name,
        "inn": company.inn,
        "balance": company.balance,
        "status": company.status,
        "settings": company.settings or {},
        "members": [
            {"user_id": m.user_id, "role": m.role, "max_concurrent_orders": m.max_concurrent_orders}
            for m in members
        ],
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }


@router.get("/companies/{company_id}/stats")
async def company_stats(company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    orders = await db.scalar(select(func.count()).select_from(Order).where(Order.company_id == company_id))
    revenue = await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.company_id == company_id, Order.status.in_(("completed", "paid", "queued", "processing"))
        )
    )
    return {"company_id": company_id, "orders": int(orders or 0), "revenue": int(revenue or 0)}


@router.get("/companies/{company_id}/logs")
async def company_logs(company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from app.models import AuditLog

    rows = (
        await db.scalars(
            select(AuditLog).where(AuditLog.company_id == company_id).order_by(AuditLog.id.desc()).limit(50)
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "action": r.action,
                "user_id": r.user_id,
                "details": r.details,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.post("/companies/{company_id}/block")
async def block_company(company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    company.status = "blocked" if company.status != "blocked" else "active"
    await db.commit()
    return {"message": "ok", "status": company.status}


@router.get("/users")
async def list_users(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(User).order_by(User.id.desc()).limit(200))).all()
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "account_type": u.account_type,
                "status": u.status,
                "staff_role": u.staff_role,
                "balance": u.balance,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in rows
        ]
    }


@router.get("/users/{user_id}")
async def get_user(user_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Не найден")
    orders_count = await db.scalar(select(func.count()).select_from(Order).where(Order.user_id == user_id))
    recent = (
        await db.scalars(select(Order).where(Order.user_id == user_id).order_by(Order.id.desc()).limit(20))
    ).all()
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "account_type": user.account_type,
        "status": user.status,
        "balance": user.balance,
        "orders_count": int(orders_count or 0),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "orders": [
            {
                "id": o.id,
                "status": o.status,
                "amount": o.amount,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in recent
        ],
    }


@router.post("/users/{user_id}/block")
async def block_user(
    user_id: int,
    body: BlockUserBody,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Не найден")
    user.status = "blocked" if body.blocked else ("active_individual" if user.account_type == "individual" else "active_legal")
    await db.commit()
    return {"message": "ok", "status": user.status}


@router.post("/users/{user_id}/delete")
async def delete_user(user_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Не найден")
    user.status = "deleted"
    user.email = f"deleted_{user.id}@removed.local"
    user.full_name = None
    await db.commit()
    return {"message": "Пользователь удалён (право на забвение)"}


@router.get("/workers")
async def list_workers(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(WorkerNode).order_by(WorkerNode.id))).all()
    lengths = await queue_service.queue_lengths()
    online = sum(1 for w in rows if w.status == "online")
    return {
        "summary": {
            "online": online,
            "total": len(rows),
            "queue_normal": lengths["normal"],
            "queue_high": lengths["high"],
        },
        "items": [
            {
                "id": w.id,
                "status": w.status,
                "gpu_name": w.gpu_name,
                "gpu_load": w.gpu_load,
                "weight": w.weight,
                "grace_period": w.grace_period,
                "last_heartbeat": w.last_heartbeat.isoformat() if w.last_heartbeat else None,
            }
            for w in rows
        ],
    }


@router.post("/workers/{worker_id}/heartbeat")
async def worker_heartbeat(
    worker_id: str,
    body: WorkerUpsert,
    db: AsyncSession = Depends(get_db),
):
    """Регистрация/heartbeat воркера (внутренний, без staff JWT — по worker_id)."""
    # Для MVP открытый heartbeat; в prod — shared secret
    node = await db.get(WorkerNode, worker_id)
    if not node:
        node = WorkerNode(id=worker_id)
        db.add(node)
    node.status = body.status
    node.gpu_name = body.gpu_name
    node.gpu_load = body.gpu_load
    node.weight = body.weight
    node.last_heartbeat = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.patch("/workers/{worker_id}/grace_period")
async def set_grace_period(
    worker_id: str,
    body: GracePeriodBody,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    node = await db.get(WorkerNode, worker_id)
    if not node:
        raise HTTPException(404, "Воркер не найден")
    node.grace_period = body.grace_period
    await db.commit()
    return {"worker_id": worker_id, "grace_period": node.grace_period}


@router.patch("/workers/{worker_id}/weight")
async def set_worker_weight(
    worker_id: str,
    weight: float = 0,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if weight < -1 or weight > 1:
        raise HTTPException(422, "Вес −1…+1")
    node = await db.get(WorkerNode, worker_id)
    if not node:
        raise HTTPException(404, "Воркер не найден")
    node.weight = weight
    await db.commit()
    return {"worker_id": worker_id, "weight": node.weight}


@router.get("/support/questions")
async def admin_support_list(_: dict = Depends(require_staff), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(SupportRequest).order_by(SupportRequest.id.desc()).limit(100))).all()
    items = []
    for r in rows:
        user = await db.get(User, r.user_id)
        items.append(
            {
                "id": r.id,
                "user_id": r.user_id,
                "user_email": user.email if user else None,
                "subject": r.subject,
                "category": r.category,
                "message": r.message,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return {"items": items}


@router.post("/support/questions/{question_id}/reply")
async def admin_support_reply(
    question_id: int,
    body: SupportQuestionRequest,
    staff: User = Depends(get_current_db_user),
    _: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    req = await db.get(SupportRequest, question_id)
    if not req:
        raise HTTPException(404, "Не найдено")
    db.add(
        SupportMessage(
            request_id=question_id,
            author_id=staff.id,
            is_staff=True,
            body=body.message,
        )
    )
    req.status = "answered"
    await db.commit()
    return {"message": "ok"}


@router.get("/legal/consents")
async def list_consents(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(UserConsent).order_by(UserConsent.id.desc()).limit(100))).all()
    items = []
    for c in rows:
        user = await db.get(User, c.user_id)
        items.append(
            {
                "id": c.id,
                "user_id": c.user_id,
                "email": user.email if user else None,
                "document_slug": c.document_slug,
                "document_version": c.document_version,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
        )
    return {"items": items}


@router.get("/queue/stats")
async def queue_stats(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    queued = await db.scalar(select(func.count()).select_from(TaskQueue).where(TaskQueue.status == "queued"))
    lengths = await queue_service.queue_lengths()
    return {"pg_queued": int(queued or 0), "redis": lengths}
