"""Администрирование: B2B, воркеры, пользователи, поддержка."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
from app.services import pii as pii_svc


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
        "settings": pii_svc.decrypt_company_settings(company.settings or {}),
        "members": [
            {"user_id": m.user_id, "role": m.role, "max_concurrent_orders": m.max_concurrent_orders}
            for m in members
        ],
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }


@router.get("/companies/{company_id}/stats")
async def company_stats(company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from app.services import shoot_links as shoot_svc

    orders = await db.scalar(select(func.count()).select_from(Order).where(Order.company_id == company_id))
    revenue = await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.company_id == company_id, Order.status.in_(("completed", "paid", "queued", "processing"))
        )
    )
    shoot = await shoot_svc.company_stats(db, company_id)
    await db.commit()
    return {
        "company_id": company_id,
        "orders": int(orders or 0),
        "revenue": int(revenue or 0),
        "shoot_links": {
            "created": shoot["created"],
            "expired": shoot["expired"],
            "success": shoot["success"],
            "active": shoot["active"],
            "conversion_rate": shoot["conversion_rate"],
        },
    }


@router.get("/companies/{company_id}/shoot-links")
async def company_shoot_links(company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Статистика shoot-link по B2B-клиенту (§3.15.4)."""
    from app.services import shoot_links as shoot_svc

    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    data = await shoot_svc.company_stats(db, company_id)
    await db.commit()
    return data


@router.get("/shoot-links/stats")
async def shoot_links_overview(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Сводка shoot-links по всем компаниям (§3.15.4)."""
    from app.services import shoot_links as shoot_svc

    data = await shoot_svc.admin_overview(db)
    await db.commit()
    return data

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


@router.get("/companies/{company_id}/invitations")
async def company_invitations(
    company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """Активные/все приглашения сотрудников компании (§11.6)."""
    from app.models import CompanyInvitation

    rows = (
        await db.scalars(
            select(CompanyInvitation)
            .where(CompanyInvitation.company_id == company_id)
            .order_by(CompanyInvitation.id.desc())
            .limit(200)
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "email": r.email,
                "role": r.role,
                "status": r.status,
                "max_concurrent_orders": r.max_concurrent_orders,
                "monthly_spending_limit": r.monthly_spending_limit,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/invitations")
async def all_invitations(
    status: str | None = Query(default="pending"),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Список приглашений по всем компаниям (§11.6, страница «Приглашения»)."""
    from app.models import CompanyInvitation

    q = (
        select(CompanyInvitation, Company.name)
        .join(Company, Company.id == CompanyInvitation.company_id, isouter=True)
        .order_by(CompanyInvitation.id.desc())
        .limit(300)
    )
    if status and status != "all":
        q = q.where(CompanyInvitation.status == status)
    rows = (await db.execute(q)).all()
    return {
        "items": [
            {
                "id": inv.id,
                "email": inv.email,
                "company_id": inv.company_id,
                "company_name": cname,
                "role": inv.role,
                "status": inv.status,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv, cname in rows
        ]
    }


@router.post("/invitations/{invitation_id}/revoke")
async def revoke_invitation(
    invitation_id: int,
    admin: User = Depends(get_current_db_user),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Отозвать приглашение (§2.5.2 / §11.6)."""
    from app.models import AuditLog, CompanyInvitation

    inv = await db.get(CompanyInvitation, invitation_id)
    if not inv:
        raise HTTPException(404, "Приглашение не найдено")
    if inv.status == "accepted":
        raise HTTPException(400, "Приглашение уже принято")
    inv.status = "revoked"
    db.add(
        AuditLog(
            company_id=inv.company_id,
            user_id=admin.id,
            action="invitation_revoked",
            details={"invitation_id": inv.id, "email": inv.email, "by": "admin"},
        )
    )
    await db.commit()
    return {"message": "ok", "status": inv.status}


@router.get("/companies/{company_id}/api-keys")
async def company_api_keys(
    company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """API-ключи компании (§11.6)."""
    from app.models import CompanyApiKey

    rows = (
        await db.scalars(
            select(CompanyApiKey)
            .where(CompanyApiKey.company_id == company_id)
            .order_by(CompanyApiKey.id.desc())
        )
    ).all()
    return {
        "items": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "is_active": k.is_active,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
            }
            for k in rows
        ]
    }


@router.post("/companies/{company_id}/api-keys/{key_id}/revoke")
async def revoke_company_api_key(
    company_id: int,
    key_id: int,
    admin: User = Depends(get_current_db_user),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Отозвать API-ключ компании (§8.8 / §11.6)."""
    from app.models import AuditLog, CompanyApiKey

    row = await db.get(CompanyApiKey, key_id)
    if not row or row.company_id != company_id:
        raise HTTPException(404, "Ключ не найден")
    row.is_active = False
    row.revoked_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            company_id=company_id,
            user_id=admin.id,
            action="api_key_revoked",
            details={"key_id": key_id, "key_prefix": row.key_prefix, "by": "admin"},
        )
    )
    await db.commit()
    return {"message": "ok"}


class MemberLimitsBody(BaseModel):
    max_concurrent_orders: int | None = Field(default=None, ge=0, le=1000)
    monthly_spending_limit: int | None = Field(default=None, ge=0)


@router.patch("/companies/{company_id}/members/{user_id}/limits")
async def set_member_limits(
    company_id: int,
    user_id: int,
    body: MemberLimitsBody,
    admin: User = Depends(get_current_db_user),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Лимиты сотрудника: max_concurrent_orders, monthly_spending_limit (§11.6)."""
    from app.models import AuditLog

    member = await db.scalar(
        select(CompanyMember).where(
            CompanyMember.company_id == company_id, CompanyMember.user_id == user_id
        )
    )
    if not member:
        raise HTTPException(404, "Сотрудник не найден")
    member.max_concurrent_orders = body.max_concurrent_orders
    member.monthly_spending_limit = body.monthly_spending_limit
    db.add(
        AuditLog(
            company_id=company_id,
            user_id=admin.id,
            action="member_limits_changed",
            details={
                "member_user_id": user_id,
                "max_concurrent_orders": body.max_concurrent_orders,
                "monthly_spending_limit": body.monthly_spending_limit,
            },
        )
    )
    await db.commit()
    return {
        "message": "ok",
        "user_id": user_id,
        "max_concurrent_orders": member.max_concurrent_orders,
        "monthly_spending_limit": member.monthly_spending_limit,
    }


class PriceOverridesBody(BaseModel):
    price_overrides: dict = Field(default_factory=dict)


@router.get("/companies/{company_id}/price-overrides")
async def get_company_price_overrides(
    company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """Индивидуальные цены компании (§11.4)."""
    from app.services import tariffs as tariff_svc

    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    settings = company.settings or {}
    overrides = settings.get("price_overrides") if isinstance(settings.get("price_overrides"), dict) else {}
    base = {t: await tariff_svc.get_amount(db, t) for t in ("small", "large", "import_glb")}
    effective = {
        t: tariff_svc.apply_company_override(base[t], overrides.get(t)) for t in base
    }
    return {"base": base, "overrides": overrides, "effective": effective}


@router.put("/companies/{company_id}/price-overrides")
async def set_company_price_overrides(
    company_id: int,
    body: PriceOverridesBody,
    admin: User = Depends(get_current_db_user),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Задать индивидуальные цены B2B: {tier: {type: fixed|percent, value: N}} (§11.4)."""
    from app.models import AuditLog

    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    clean: dict = {}
    for tier, ov in (body.price_overrides or {}).items():
        if tier not in ("small", "large", "import_glb"):
            continue
        if not isinstance(ov, dict):
            continue
        typ = str(ov.get("type") or "").lower()
        val = ov.get("value")
        if typ not in ("fixed", "percent") or not isinstance(val, (int, float)):
            continue
        if typ == "percent" and not (0 <= val <= 100):
            continue
        if val < 0:
            continue
        clean[tier] = {"type": typ, "value": int(val)}
    settings = dict(company.settings or {})
    if clean:
        settings["price_overrides"] = clean
    else:
        settings.pop("price_overrides", None)
    company.settings = settings
    db.add(
        AuditLog(
            company_id=company_id,
            user_id=admin.id,
            action="company_price_overrides_changed",
            details={"price_overrides": clean},
        )
    )
    await db.commit()
    return {"message": "ok", "price_overrides": clean}


@router.get("/support/stats")
async def admin_support_stats(_: dict = Depends(require_staff), db: AsyncSession = Depends(get_db)):
    """Статистика поддержки: SLA, первый ответ, нагрузка агентов (§11.9)."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    total = await db.scalar(select(func.count()).select_from(SupportRequest)) or 0
    open_cnt = await db.scalar(
        select(func.count()).select_from(SupportRequest).where(
            SupportRequest.status.in_(("new", "in_progress"))
        )
    ) or 0
    answered_cnt = await db.scalar(
        select(func.count()).select_from(SupportRequest).where(SupportRequest.status == "answered")
    ) or 0
    week_cnt = await db.scalar(
        select(func.count()).select_from(SupportRequest).where(SupportRequest.created_at >= week_ago)
    ) or 0

    # среднее время первого ответа (первый staff-ответ - создание обращения)
    first_replies = (
        await db.execute(
            select(
                SupportRequest.id,
                SupportRequest.created_at,
                func.min(SupportMessage.created_at),
            )
            .join(SupportMessage, SupportMessage.request_id == SupportRequest.id)
            .where(SupportMessage.is_staff.is_(True))
            .group_by(SupportRequest.id, SupportRequest.created_at)
        )
    ).all()
    deltas = [
        (reply - created).total_seconds()
        for _rid, created, reply in first_replies
        if created and reply
    ]
    avg_first_response_sec = int(sum(deltas) / len(deltas)) if deltas else None

    # нагрузка по агентам (staff-сообщения)
    agent_rows = (
        await db.execute(
            select(SupportMessage.author_id, func.count())
            .where(SupportMessage.is_staff.is_(True))
            .group_by(SupportMessage.author_id)
            .order_by(func.count().desc())
            .limit(20)
        )
    ).all()
    agents = []
    for author_id, cnt in agent_rows:
        email = None
        if author_id:
            u = await db.get(User, author_id)
            email = u.email if u else None
        agents.append({"agent_id": author_id, "email": email, "replies": int(cnt)})

    return {
        "total_tickets": int(total),
        "open_tickets": int(open_cnt),
        "answered_tickets": int(answered_cnt),
        "tickets_7d": int(week_cnt),
        "avg_first_response_sec": avg_first_response_sec,
        "agents": agents,
    }


@router.post("/companies/{company_id}/block")
async def block_company(company_id: int, _: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    company.status = "blocked" if company.status != "blocked" else "active"
    await db.commit()
    return {"message": "ok", "status": company.status}


class CompanySettingsPatch(BaseModel):
    force_trellis_version: str | None = None


@router.patch("/companies/{company_id}/settings")
async def patch_company_settings(
    company_id: int,
    body: CompanySettingsPatch,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """§18.4.2 — принудительная версия TRELLIS для заказов компании."""
    from app.services import trellis_rollout as tr

    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Компания не найдена")
    settings = dict(company.settings or {})
    if body.force_trellis_version is not None:
        ftv = str(body.force_trellis_version).strip()
        if ftv.lower() in ("", "default", "none", "null"):
            settings.pop("force_trellis_version", None)
        else:
            settings["force_trellis_version"] = tr.normalize_version(ftv) or ftv
    company.settings = settings
    await db.commit()
    return {
        "company_id": company_id,
        "force_trellis_version": settings.get("force_trellis_version"),
    }


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


@router.get("/users/{user_id}/audit")
async def admin_user_audit_log(
    user_id: int,
    action: str | None = Query(None),
    action_prefix: str | None = Query(None, description="Например oauth_"),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Audit_log пользователя для support §2.2.3."""
    from app.services import audit_query as aq

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Не найден")
    return await aq.list_audit_logs(
        db,
        action=action,
        action_prefix=action_prefix,
        user_id=user_id,
        days=days,
        limit=limit,
        offset=offset,
    )


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
async def delete_user(user_id: int, admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Право на забвение: полное удаление ПДн, финансы анонимизируются (§11.12)."""
    from app.services import account_deletion as del_svc

    result = await del_svc.execute_deletion(db, user_id=user_id, processed_by=int(admin.get("sub") or 0) or None)
    await db.commit()
    return {"message": "Пользователь удалён (право на забвение)", **result}


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
                "trellis_version": (w.meta or {}).get("trellis_version") or (w.meta or {}).get("version"),
                "docker_image": (w.meta or {}).get("docker_image"),
                "maintenance": bool((w.meta or {}).get("maintenance")),
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


class TrellisRolloutBody(BaseModel):
    target_version: str = "2"
    default_docker_image: str | None = None
    allowed_versions: list[str] | None = None


class WorkerTrellisBody(BaseModel):
    trellis_version: str
    docker_image: str | None = None


class WorkerMaintenanceBody(BaseModel):
    enabled: bool = True


@router.get("/trellis/rollout")
async def trellis_rollout_get(_: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """§18.3 — конфиг rolling update."""
    from app.services import trellis_rollout as tr

    return await tr.get_rollout_config(db)


@router.put("/trellis/rollout")
async def trellis_rollout_put(
    body: TrellisRolloutBody,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import trellis_rollout as tr

    result = await tr.put_rollout_config(
        db,
        target_version=body.target_version,
        default_docker_image=body.default_docker_image,
        allowed_versions=body.allowed_versions,
        user_id=int(admin.get("sub") or 0) or None,
    )
    await db.commit()
    return result


@router.get("/trellis/history")
async def trellis_history(
    limit: int = 50,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import trellis_rollout as tr

    return {"items": await tr.list_history(db, limit=limit)}


@router.post("/workers/{worker_id}/maintenance")
async def worker_maintenance(
    worker_id: str,
    body: WorkerMaintenanceBody,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import trellis_rollout as tr

    result = await tr.set_worker_maintenance(
        db, worker_id, enabled=body.enabled, user_id=int(admin.get("sub") or 0) or None
    )
    await db.commit()
    return result


@router.post("/workers/{worker_id}/trellis/rollback")
async def worker_trellis_rollback(
    worker_id: str,
    body: WorkerTrellisBody,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """§18.4.1 откат воркера на предыдущий образ."""
    from app.services import trellis_rollout as tr

    result = await tr.rollback_worker(
        db,
        worker_id,
        trellis_version=body.trellis_version,
        docker_image=body.docker_image,
        user_id=int(admin.get("sub") or 0) or None,
    )
    await db.commit()
    return result


@router.post("/workers/{worker_id}/trellis/rollout")
async def worker_trellis_rollout(
    worker_id: str,
    body: WorkerTrellisBody | None = None,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """§18.3.2 rolling update — maintenance + target version."""
    from app.services import trellis_rollout as tr

    payload = body or WorkerTrellisBody(trellis_version="2")
    result = await tr.rollout_worker(
        db,
        worker_id,
        trellis_version=payload.trellis_version,
        docker_image=payload.docker_image,
        user_id=int(admin.get("sub") or 0) or None,
    )
    await db.commit()
    return result


@router.post("/workers/{worker_id}/trellis/complete")
async def worker_trellis_complete(
    worker_id: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import trellis_rollout as tr

    result = await tr.clear_worker_maintenance(
        db, worker_id, user_id=int(admin.get("sub") or 0) or None
    )
    await db.commit()
    return result


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
    try:
        from app.services import push as push_svc

        user = await db.get(User, req.user_id)
        if user and push_svc.user_wants_notification(user, "support_reply"):
            preview = (body.message or "")[:120]
            await push_svc.send_to_user(
                db,
                req.user_id,
                "Ответ поддержки",
                preview or "Новое сообщение по вашему обращению",
                data={
                    "type": "support_reply",
                    "event": "support_reply",
                    "ticket_id": str(question_id),
                    "deeplink": f"kworkmob://open/support/ticket/{question_id}",
                },
                email_fallback=True,
            )
            await db.commit()
    except Exception:  # noqa: BLE001
        pass
    return {"message": "ok"}


@router.post("/support/questions/{question_id}/ai-suggest")
async def admin_support_ai_suggest(
    question_id: int,
    _: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Черновик ответа через Ollama (§4.8.11 / §14.4)."""
    from app.services.ollama import ollama_service

    req = await db.get(SupportRequest, question_id)
    if not req:
        raise HTTPException(404, "Не найдено")
    health = await ollama_service.health()
    if not health.get("ok"):
        raise HTTPException(
            503,
            detail={
                "code": "ollama_unavailable",
                "message": "ИИ-помощник временно недоступен",
                "health": health,
            },
        )
    messages = (
        await db.scalars(
            select(SupportMessage)
            .where(SupportMessage.request_id == question_id)
            .order_by(SupportMessage.id)
        )
    ).all()
    ctx_lines = [f"{'staff' if m.is_staff else 'user'}: {m.body}" for m in messages[-10:]]
    question = req.message or (messages[0].body if messages else "")
    try:
        text = await ollama_service.suggest_reply(question, context="\n".join(ctx_lines))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, detail={"code": "ollama_error", "message": str(exc)[:200]}) from exc
    return {
        "suggestion": text,
        "model": settings.OLLAMA_MODEL,
        "available": bool(text),
    }


@router.get("/support/ollama/status")
async def ollama_status(_: dict = Depends(require_staff)):
    from app.services.ollama import ollama_service

    health = await ollama_service.health()
    return {
        "url": settings.OLLAMA_URL,
        "model": settings.OLLAMA_MODEL,
        **health,
    }


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


@router.get("/metrics/publication-funnel")
async def publication_funnel(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    company_id: int | None = Query(None),
    category: str | None = Query(None),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Воронка публикации §7.9.1."""
    from app.services import publication_funnel as funnel_svc

    data = await funnel_svc.global_funnel(
        db,
        date_from=date_from,
        date_to=date_to,
        company_id=company_id,
        category=category,
    )
    await db.commit()
    return data


@router.get("/metrics/publication-funnel/export")
async def publication_funnel_export(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    company_id: int | None = Query(None),
    category: str | None = Query(None),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import publication_funnel as funnel_svc
    from fastapi.responses import Response

    data = await funnel_svc.global_funnel(
        db,
        date_from=date_from,
        date_to=date_to,
        company_id=company_id,
        category=category,
    )
    await db.commit()
    body = funnel_svc.funnel_to_csv(data)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="publication-funnel.csv"'},
    )


@router.get("/metrics/dashboard")
async def metrics_dashboard(_: dict = Depends(require_admin)):
    """Агрегаты ClickHouse для admin dashboard (§12)."""
    from app.services.metrics import dashboard_aggregates

    return await dashboard_aggregates()


@router.get("/analytics/screens")
async def analytics_screen_breakdown(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, ge=1, le=200),
    screen_category: str | None = Query(default=None, pattern=r"^(oauth|app)$"),
    export: str | None = Query(default=None, alias="format"),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """screen_view breakdown из CH MV / PG fallback §19.20."""
    from fastapi.responses import Response

    from app.services import analytics_query as aq

    data = await aq.screen_breakdown(db, days=days, limit=limit, screen_category=screen_category)
    if export == "csv":
        return Response(
            content=aq.screens_to_csv(data),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="analytics-screens.csv"'},
        )
    return data


@router.get("/analytics/events")
async def analytics_raw_events(
    user_id: int | None = Query(default=None),
    event: str | None = Query(default=None, max_length=64),
    screen: str | None = Query(default=None, max_length=64),
    screen_category: str | None = Query(default=None, pattern=r"^(oauth|app)$"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    export: str | None = Query(default=None, alias="format"),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Raw mobile analytics events из PG §19.20."""
    from fastapi.responses import Response

    from app.services import analytics_query as aq

    data = await aq.list_raw_events(
        db,
        user_id=user_id,
        event=event,
        screen=screen,
        screen_category=screen_category,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    if export == "csv":
        return Response(
            content=aq.raw_events_to_csv(data),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="analytics-events.csv"'},
        )
    return data


@router.get("/analytics/screens/timeseries")
async def analytics_screen_timeseries(
    days: int = Query(default=14, ge=1, le=90),
    top: int = Query(default=8, ge=1, le=20),
    screen: str | None = Query(default=None, max_length=64),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """screen_view по дням (top screens) §19.20."""
    from app.services import analytics_query as aq

    return await aq.screen_timeseries(db, days=days, top=top, screen=screen or None)


@router.post("/analytics/alerts/check")
async def analytics_alerts_check(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Проверка PG→CH backlog → Telegram/email §19.20."""
    from app.services import analytics_alerts as aa

    result = await aa.check_and_alert(db)
    await db.commit()
    return result


@router.get("/analytics/status")
async def analytics_sync_status(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """PG→CH sync backlog §19.20."""
    from app.services import analytics_query as aq
    from app.services.metrics import record_analytics_ch_pending

    data = await aq.analytics_sync_status(db)
    record_analytics_ch_pending(data["pending_ch_sync"])
    return data


@router.get("/analytics/campaign-banner-ctr")
async def analytics_campaign_banner_ctr(
    days: int = Query(default=30, ge=1, le=90),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """In-app banner CTR по campaign_id §19.20."""
    from app.services import analytics_query as aq

    return await aq.campaign_banner_ctr(db, days=days)


@router.post("/analytics/sync")
async def analytics_sync_ch(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ручной PG→CH sync несинхронизированных событий §19.20."""
    from app.services import analytics_sync as asy

    result = await asy.sync_unsynced(db)
    await db.commit()
    from app.services.metrics import record_analytics_ch_pending

    record_analytics_ch_pending(result.get("pending", 0))
    return result


@router.get("/audit")
async def admin_audit_log(
    action: str | None = Query(None),
    action_prefix: str | None = Query(None, description="Например oauth_"),
    user_id: int | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Глобальный audit_log §2.2.3 / §10.7.7."""
    from app.services import audit_query as aq

    return await aq.list_audit_logs(
        db,
        action=action,
        action_prefix=action_prefix,
        user_id=user_id,
        days=days,
        limit=limit,
        offset=offset,
    )


@router.get("/audit/oauth-summary")
async def admin_audit_oauth_summary(
    days: int = Query(7, ge=1, le=90),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Сводка oauth_* в audit_log для AnalyticsPage §2.2.3."""
    from app.services import audit_query as aq

    return await aq.oauth_audit_summary(db, days=days)


@router.get("/access-log")
async def admin_access_log(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    company_id: int | None = Query(None),
    user_id: int | None = Query(None),
    model_uuid: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Глобальный аудит скачиваний моделей §10.7.2."""
    from app.services import access_log as access_svc

    return await access_svc.list_access_logs(
        db,
        company_id=company_id,
        user_id=user_id,
        model_uuid=model_uuid,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/access-log/export")
async def admin_access_log_export(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    company_id: int | None = Query(None),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response

    from app.services import access_log as access_svc

    data = await access_svc.list_access_logs(
        db,
        company_id=company_id,
        date_from=date_from,
        date_to=date_to,
        limit=5000,
    )
    return Response(
        content=access_svc.to_csv(data["items"]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="access-log.csv"'},
    )


@router.post("/audit-export/run")
async def run_audit_export(
    year: int | None = Query(None),
    month: int | None = Query(None),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ручной запуск экспорта в MinIO audit-logs §10.7.7."""
    from app.services import audit_export as ae

    return await ae.export_month(db, year=year, month=month)


@router.post("/storage-alerts/check")
async def run_storage_alerts_check(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ручная проверка SMART/disk → Telegram."""
    from app.services import storage_alerts as sa

    return await sa.check_and_alert(db)


@router.post("/ops-alerts/check")
async def run_ops_alerts_check(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ручная проверка queue / all-busy / worker offline §12.4.1."""
    from app.services import ops_alerts as oa

    return await oa.check_and_alert(db)


@router.get("/age-verifications")
async def admin_age_verifications(
    success: bool | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Просмотр проверок возраста 18+ (§10.8.3 / §11 модерация)."""
    from app.services import age_admin as aa

    return await aa.list_age_verifications(db, limit=limit, success=success)


@router.get("/age-verifications/export")
async def admin_age_verifications_export(
    success: bool | None = Query(None),
    limit: int = Query(5000, ge=1, le=10000),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """CSV экспорт проверок возраста (§11)."""
    from fastapi.responses import Response

    from app.services import age_admin as aa

    data = await aa.list_age_verifications(db, limit=limit, success=success)
    return Response(
        content=aa.to_csv(data["events"]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="age-verifications.csv"'},
    )


@router.post("/corporate-alerts/check")
async def run_corporate_alerts_check(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ручной scan low-balance (§12.4.1)."""
    from app.services import corporate_alerts as ca

    return await ca.scan_low_balances(db)


@router.get("/yookassa/error-streak")
async def yookassa_error_streak(_: dict = Depends(require_admin)):
    from app.services import yookassa_alerts as yk

    return {"streak": await yk.current_streak(), "threshold": yk._threshold()}


@router.get("/soft-launch/kpi")
async def soft_launch_kpi(
    days: int = Query(7, ge=1, le=90),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Live soft-launch KPI: воронка, заказы, конверсия ≥60%."""
    from app.services import soft_launch as sl

    return await sl.soft_launch_kpi(db, days=days)


@router.get("/soft-launch/kpi/export")
async def soft_launch_kpi_export(
    days: int = Query(7, ge=1, le=90),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """CSV export soft-launch KPI."""
    from fastapi.responses import Response

    from app.services import soft_launch as sl

    data = await sl.soft_launch_kpi(db, days=days)
    return Response(
        content=sl.kpi_to_csv(data),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="soft-launch-kpi-{days}d.csv"'},
    )


@router.get("/write-activity")
async def write_activity_status(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Write Activity Heartbeat snapshot §11.16 / §23.4."""
    from app.services import write_activity as wa

    return await wa.snapshot_write_activity(db)


@router.post("/write-activity/check")
async def write_activity_check(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ручная проверка stale write → alert."""
    from app.services import write_activity as wa

    return await wa.check_and_alert(db)


@router.post("/storage/force-resync-minio")
async def force_resync_minio(
    staff: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Force Resync MinIO §11.16.4."""
    from app.services import storage_ops as so

    uid = int(staff["sub"]) if staff.get("sub") else None
    return await so.force_resync_minio(db, user_id=uid)


@router.post("/storage/restart-patroni-replication")
async def restart_patroni_replication(
    staff: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Restart Patroni Replication §11.16.4."""
    from app.services import storage_ops as so

    uid = int(staff["sub"]) if staff.get("sub") else None
    return await so.restart_patroni_replication(db, user_id=uid)


@router.post("/storage/fio-test")
async def fio_disk_test(
    staff: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    node: str | None = Query(None, description="Узел A/B опционально"),
):
    """Запустить FIO-тест диска (~10 сек) §11.16.4."""
    from app.services import storage_ops as so

    uid = int(staff["sub"]) if staff.get("sub") else None
    return await so.run_fio_disk_test(db, user_id=uid, node=node)


@router.get("/storage/docker-logs")
async def storage_docker_logs(
    container: str = Query(..., description="Имя контейнера"),
    limit: int = Query(200, ge=1, le=2000),
    minutes: int = Query(60, ge=1, le=1440),
    _: dict = Depends(require_admin),
):
    """Посмотреть docker logs через Loki / proxy §11.16.4."""
    from app.services import loki_logs as ll

    return await ll.fetch_container_logs(container=container, limit=limit, minutes=minutes)


@router.get("/storage/docker-logs/containers")
async def storage_docker_log_containers(_: dict = Depends(require_admin)):
    from app.services import loki_logs as ll

    return {"containers": ll.configured_containers()}


@router.get("/soft-launch/checklist")
async def soft_launch_checklist_get(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Чек-лист soft launch (backend, не localStorage)."""
    from app.services import soft_launch as sl

    return await sl.get_checklist(db)


@router.put("/soft-launch/checklist")
async def soft_launch_checklist_put(
    body: dict,
    staff: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Сохранить чек-лист soft launch."""
    from app.services import soft_launch as sl

    checks = body.get("checks") if isinstance(body.get("checks"), dict) else body
    if not isinstance(checks, dict):
        from fastapi import HTTPException

        raise HTTPException(400, "checks object required")
    uid = int(staff["sub"]) if staff.get("sub") else None
    result = await sl.put_checklist(db, checks=checks, user_id=uid)
    await db.commit()
    return result


@router.get("/maintenance/checklist")
async def maintenance_checklist_get(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Чек-лист планового обслуживания §23.7."""
    from app.services import maintenance as mt

    return await mt.get_checklist(db)


@router.put("/maintenance/checklist")
async def maintenance_checklist_put(
    body: dict,
    staff: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import maintenance as mt

    checks = body.get("checks") if isinstance(body.get("checks"), dict) else body
    if not isinstance(checks, dict):
        raise HTTPException(400, "checks object required")
    uid = int(staff["sub"]) if staff.get("sub") else None
    result = await mt.put_checklist(db, checks=checks, user_id=uid)
    await db.commit()
    return result


@router.post("/maintenance/cleanup-logs")
async def maintenance_cleanup_logs(
    staff: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    older_than_days: int | None = Query(None, ge=1, le=365),
):
    """Очистка старых service logs §23.7."""
    from app.services import maintenance as mt

    uid = int(staff["sub"]) if staff.get("sub") else None
    return await mt.cleanup_service_logs(db, user_id=uid, older_than_days=older_than_days)


@router.post("/maintenance/backup-restore-test")
async def maintenance_backup_restore_test(
    staff: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Тест восстановления из бэкапа §23.7."""
    from app.services import maintenance as mt

    uid = int(staff["sub"]) if staff.get("sub") else None
    return await mt.backup_restore_test(db, user_id=uid)


@router.post("/source-expire/notify")
async def source_expire_notify_now(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ручной прогон уведомлений об истечении исходников §9.1.2."""
    from app.services import source_expire as se

    return await se.notify_expiring_sources(db)


@router.get("/storage/node-timeline")
async def storage_node_timeline(
    days: int = Query(7, ge=1, le=90),
    node_id: str | None = Query(None),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """История доступности узлов §11.16.3."""
    from app.services import node_timeline as nt

    return await nt.node_timeline(db, days=days, node_id=node_id)


@router.get("/storage/node-timeline/export")
async def storage_node_timeline_export(
    days: int = Query(7, ge=1, le=90),
    node_id: str | None = Query(None),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """CSV экспорт timeline §11.16.3."""
    from fastapi.responses import Response

    from app.services import node_timeline as nt

    data = await nt.node_timeline(db, days=days, node_id=node_id)
    content = "\ufeff" + nt.timeline_to_csv(data)
    suffix = f"_{node_id}" if node_id else ""
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="node_timeline{suffix}.csv"'},
    )


@router.post("/storage/node-timeline/sample")
async def storage_node_timeline_sample(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import node_timeline as nt

    return await nt.record_node_heartbeats(db)


@router.get("/storage/disk-forecast")
async def storage_disk_forecast(
    days: int = Query(14, ge=1, le=90),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Прогноз заполнения диска + wearout §23.7."""
    from app.services import disk_forecast as df

    return await df.disk_forecast(db, days_lookback=days)


@router.post("/storage/disk-forecast/sample")
async def storage_disk_forecast_sample(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import disk_forecast as df

    return await df.sample_disk_usage(db)


@router.get("/webhooks/deliveries/dashboard")
async def admin_webhook_deliveries_dashboard(
    company_id: int | None = Query(None),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """B2B webhook retries / DLQ dashboard §14.5.4."""
    from app.services import company_webhooks as wh

    return await wh.delivery_dashboard(db, company_id=company_id)


@router.get("/webhooks/deliveries/{delivery_id}")
async def admin_webhook_delivery_detail(
    delivery_id: int,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_webhooks as wh

    return await wh.admin_get_delivery(db, delivery_id)


@router.post("/webhooks/deliveries/{delivery_id}/retry")
async def admin_webhook_delivery_retry(
    delivery_id: int,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import company_webhooks as wh

    result = await wh.admin_retry_delivery(db, delivery_id)
    await db.commit()
    return result


@router.post("/shoot-links/cleanup-photos")
async def run_shoot_photo_cleanup(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ручной TTL cleanup фото shoot-link §3.15.4."""
    from app.services import shoot_cleanup as sc

    return await sc.cleanup_stale_photos(db)


@router.post("/quality-alerts/check")
async def run_quality_alerts_check(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ручная проверка publication conversion / fallback segmentation §12.4.1."""
    from app.services import quality_alerts as qa

    return await qa.check_and_alert(db)


@router.get("/well-known/apple-app-site-association")
async def apple_app_site_association(_: dict = Depends(require_admin)):
    """Превью AASA с env TEAMID (prod host = SELLER_PUBLIC_URL)."""
    from app.services import applinks as al

    return al.apple_app_site_association()


@router.get("/well-known/assetlinks")
async def android_assetlinks(_: dict = Depends(require_admin)):
    from app.services import applinks as al

    return al.android_assetlinks()
