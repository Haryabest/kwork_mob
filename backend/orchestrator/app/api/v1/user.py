"""Пользователь: профиль, баланс, транзакции, модели, device tokens."""

from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user
from app.models import DeviceToken, Model3D, Order, Transaction, User
from app.schemas.auth import AccountTypeRequest
from app.schemas.balance_filters import BalanceFiltersBody, CompanyBalanceFiltersBody
from app.services import auth as auth_service
from app.services import pii as pii_svc

router = APIRouter()


class TopupRequest(BaseModel):
    amount: int = Field(default=1000, ge=100, le=500_000)
    payment_method: str = Field(default="redirect", pattern=r"^(redirect|sbp_qr|card|sbp)$")
    customer_name: str | None = Field(default=None, max_length=255)


class DeviceTokenRequest(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    platform: str = Field(default="android", pattern=r"^(android|ios|web)$")
    app_version: str | None = Field(default=None, max_length=32)


def _user_payload(user: User) -> dict:
    pii = pii_svc.user_public(user)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": pii["full_name"],
        "phone": pii["phone"],
        "inn": pii["inn"],
        "account_type": user.account_type,
        "status": user.status,
        "email_verified": user.email_verified,
        "staff_role": user.staff_role,
        "role": user.staff_role or "user",
        "balance": user.balance,
        "marketing_opt_in": user.marketing_opt_in,
        "notification_prefs": dict(user.notification_prefs or {}),
        "totp_enabled": bool(user.totp_enabled),
        "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
        "age_verified": bool(user.age_verified_at),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "export_format": (user.notification_prefs or {}).get("export_format", "glb"),
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_db_user)):
    """Текущий пользователь (для seller и staff)."""
    return _user_payload(user)


@router.patch("/me")
async def update_me(
    payload: dict,
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновление профиля (ФИО, телефон, маркетинг)."""
    changed: list[str] = []
    if "full_name" in payload or "phone" in payload or "inn" in payload:
        changed = pii_svc.encrypt_user_fields(
            user,
            {k: payload[k] for k in ("full_name", "phone", "inn") if k in payload},
        )
    if "marketing_opt_in" in payload:
        user.marketing_opt_in = bool(payload["marketing_opt_in"])
    if "notification_prefs" in payload and isinstance(payload["notification_prefs"], dict):
        allowed = {
            "generation_done",
            "refund",
            "source_expire",
            "cleanup",
            "publish_reminder",
            "push_enabled",
            "email_enabled",
            "email_orders",
            "email_balance",
            "nsfw_blocked",
            "topup_failed",
            "support_reply",
            "export_format",
        }
        cur = dict(user.notification_prefs or {})
        for k, v in payload["notification_prefs"].items():
            if k in allowed:
                cur[k] = bool(v)
        user.notification_prefs = cur
    if "export_format" in payload and payload["export_format"] in ("glb", "usdz"):
        cur = dict(user.notification_prefs or {})
        cur["export_format"] = payload["export_format"]
        user.notification_prefs = cur
    if changed:
        ip = request.client.host if request.client else None
        await pii_svc.audit_pii_change(
            db,
            user_id=user.id,
            action="user.profile_update",
            fields=changed,
            ip=ip,
        )
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


@router.get("/balance-filters")
async def get_balance_filters(user: User = Depends(get_current_db_user)):
    """Saved personal transaction filters §20.3.4."""
    from app.services import balance_filters as bf

    return {"scope": "personal", "filters": bf.get_personal_filters(user)}


@router.put("/balance-filters")
async def put_balance_filters(
    body: BalanceFiltersBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist personal transaction filters §20.3.4."""
    from app.services import balance_filters as bf

    saved = await bf.save_personal_filters(db, user, body.model_dump())
    await db.commit()
    return {"scope": "personal", "filters": saved}


@router.get("/transactions")
async def get_transactions(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    tx_type: str = Query(default="all", alias="type", pattern=r"^(all|topup|charge|refund)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    from app.services import company_balance as bal
    from app.services import pending_payments as pend

    stmt = bal.build_user_tx_stmt(
        user.id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    tx_total = await bal.count_user_transactions(
        db,
        user.id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    pending_items = await pend.list_pending_dicts(
        db,
        user_id=user.id,
        personal_only=True,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    pending_count = len(pending_items)
    total = int(tx_total) + pending_count

    if offset < pending_count:
        tx_offset = 0
        tx_limit = max(0, limit - (pending_count - offset))
    else:
        tx_offset = offset - pending_count
        tx_limit = limit

    rows = (await db.scalars(stmt.offset(tx_offset).limit(tx_limit))).all()
    tx_items = [bal.transaction_to_dict(t) for t in rows]

    if offset < pending_count:
        page = pending_items[offset : offset + limit]
        need = limit - len(page)
        if need > 0:
            page.extend(tx_items[:need])
    else:
        page = tx_items

    return {
        "items": page,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/transactions/export")
async def export_user_transactions(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    tx_type: str = Query(default="all", alias="type", pattern=r"^(all|topup|charge|refund)$"),
):
    """CSV выгрузка личных транзакций §20.3.4."""
    from fastapi.responses import Response

    from app.services import company_balance as bal

    csv_body = await bal.export_user_transactions_csv(
        db,
        user_id=user.id,
        date_from=date_from,
        date_to=date_to,
        tx_type=tx_type,
    )
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


@router.post("/balance/topup")
async def topup_balance(
    body: TopupRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Пополнение: карта (redirect) или СБП QR + фискальный чек (§8.12 / §8.6.4)."""
    from app.core.config import settings
    from app.services.tax import build_receipt_for_payment
    from app.services.yookassa import yookassa_service

    amount = body.amount

    # Локальная разработка без ключей ЮKassa
    if settings.is_development and not yookassa_service.configured:
        user.balance += amount
        db.add(
            Transaction(
                user_id=user.id,
                amount=amount,
                tx_type="topup",
                description="Dev mock пополнение (без ЮKassa)",
            )
        )
        await db.commit()
        return {
            "id": f"dev-topup-{user.id}",
            "status": "succeeded",
            "amount": amount,
            "balance": user.balance,
            "dev_mock": True,
        }

    method = body.payment_method
    if method == "card":
        method = "redirect"
    if method == "sbp":
        method = "sbp_qr"

    description = f"Пополнение баланса KWork Mob ({user.email})"
    receipt = await build_receipt_for_payment(
        db,
        customer_email=user.email,
        description=description,
        amount_rub=amount,
        customer_name=body.customer_name or pii_svc.user_public(user).get("full_name"),
    )
    payment = await yookassa_service.create_payment(
        amount,
        description,
        return_url=f"{settings.SELLER_PUBLIC_URL}/balance",
        metadata={
            "purpose": "topup",
            "user_id": str(user.id),
            "amount": str(amount),
            "payment_method": method,
        },
        payment_method=method,  # type: ignore[arg-type]
        receipt=receipt,
        idempotence_key=f"topup-{user.id}-{amount}-{method}",
    )
    from app.services import pending_payments as pend

    await pend.upsert_pending(
        db,
        payment_id=payment["id"],
        user_id=user.id,
        amount=amount,
        payment_method=method,
        purpose="topup",
    )
    await db.commit()
    return {
        "id": payment["id"],
        "status": payment["status"],
        "confirmation_url": payment.get("confirmation_url"),
        "confirmation_data": payment.get("confirmation_data"),
        "confirmation_type": payment.get("confirmation_type"),
        "payment_method": method,
        "amount": amount,
        "receipt": True,
        "payment_id": payment["id"],
    }


@router.get("/balance/payment/{payment_id}")
async def topup_payment_status(
    payment_id: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Polling статуса пополнения (СБП QR / карта) §20.3.3."""
    from app.core.config import settings
    from app.services.yookassa import yookassa_service

    if payment_id.startswith("dev-topup-"):
        await db.refresh(user)
        return {"status": "succeeded", "payment_id": payment_id, "balance": user.balance, "dev_mock": True}

    if not yookassa_service.configured:
        if settings.is_development:
            await db.refresh(user)
            return {"status": "pending", "payment_id": payment_id, "balance": user.balance}
        raise HTTPException(503, "ЮKassa не настроена")

    payment = await yookassa_service.get_payment(payment_id)
    meta = payment.get("metadata") or {}
    if str(meta.get("user_id")) != str(user.id):
        raise HTTPException(403, "Платёж принадлежит другому пользователю")
    await db.refresh(user)
    tx = await db.scalar(select(Transaction).where(Transaction.external_id == payment_id))
    status = payment.get("status") or "pending"
    if tx or status == "succeeded":
        status = "succeeded"
    elif status == "canceled":
        from app.services import pending_payments as pend

        await pend.mark_status(db, payment_id, "canceled")
        await db.commit()
    return {
        "status": status,
        "payment_id": payment_id,
        "balance": user.balance,
        "amount": int(float((payment.get("amount") or {}).get("value") or 0)),
    }


@router.get("/notifications")
async def list_notifications(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Inbox уведомлений §19.16."""
    from app.services import notification_inbox as inbox_svc

    rows, total = await inbox_svc.list_for_user(db, user.id, limit=limit, offset=offset)
    unread = await inbox_svc.unread_count(db, user.id)
    return {
        "items": [
            {
                "id": r.id,
                "title": r.title,
                "body": r.body,
                "type": r.event_type,
                "order_id": r.order_id,
                "model_uuid": r.model_uuid,
                "read": r.read_at is not None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": total,
        "unread": unread,
        "limit": limit,
        "offset": offset,
    }


@router.post("/notifications/read-all")
async def notifications_read_all(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import notification_inbox as inbox_svc

    n = await inbox_svc.mark_all_read(db, user.id)
    await db.commit()
    return {"marked": n}


@router.post("/notifications/{notification_id}/read")
async def notification_mark_read(
    notification_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import notification_inbox as inbox_svc

    ok = await inbox_svc.mark_read(db, user.id, notification_id)
    if not ok:
        raise HTTPException(404, "Уведомление не найдено")
    await db.commit()
    return {"ok": True}


@router.delete("/notifications")
async def notifications_clear(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import notification_inbox as inbox_svc

    n = await inbox_svc.clear_all(db, user.id)
    await db.commit()
    return {"deleted": n}


@router.post("/me/delete-request")
async def request_account_deletion(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Право на забвение: заявка, SLA 30 дней (§2.8.3)."""
    from app.services import account_deletion as del_svc

    row = await del_svc.request_deletion(db, user)
    await db.commit()
    return {
        "id": row.id,
        "status": row.status,
        "requested_at": row.requested_at.isoformat() if row.requested_at else None,
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "message": "Запрос принят. Удаление ПДн в течение 30 дней; финансы анонимизируются и хранятся 5 лет.",
    }


@router.get("/models")
async def list_user_models(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
    company_id: int | None = Query(default=None),
):
    from app.services import model_storage as ms
    from app.services.access import assert_company_access

    if company_id is not None:
        await assert_company_access(db, user, company_id)
        where = (Model3D.company_id == company_id, Model3D.trashed_at.is_(None))
    else:
        where = (Model3D.user_id == user.id, Model3D.trashed_at.is_(None))

    rows = (
        await db.execute(
            select(Model3D, Order.category, Order.tier, Order.status)
            .outerjoin(Order, Model3D.order_id == Order.id)
            .where(*where)
            .order_by(Model3D.id.desc())
            .limit(100)
        )
    ).all()

    return {
        "items": [
            {
                "uuid": m.uuid,
                "order_id": m.order_id,
                "display_name": m.display_name,
                "category": category,
                "tier": tier,
                "glb_url": m.glb_url,
                "usdz_url": m.usdz_url,
                "publish_status": m.publish_status,
                "order_status": order_status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "storage": ms.storage_meta(m),
            }
            for m, category, tier, order_status in rows
        ],
        "scope": "company" if company_id else "personal",
    }


@router.post("/devices")
async def register_device(
    body: DeviceTokenRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Регистрация FCM/APNs токена (§3.4.3)."""
    existing = await db.scalar(select(DeviceToken).where(DeviceToken.token == body.token))
    if existing:
        existing.user_id = user.id
        existing.platform = body.platform
        existing.app_version = body.app_version
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(
            DeviceToken(
                user_id=user.id,
                token=body.token,
                platform=body.platform,
                app_version=body.app_version,
            )
        )
    await db.commit()
    return {"ok": True}


@router.delete("/devices")
async def unregister_device(
    body: DeviceTokenRequest,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.scalar(
        select(DeviceToken).where(DeviceToken.token == body.token, DeviceToken.user_id == user.id)
    )
    if row:
        await db.delete(row)
        await db.commit()
    return {"ok": True}


class DraftBackupPrepareBody(BaseModel):
    model_uuid: str = Field(min_length=36, max_length=36)
    category: str | None = None
    captured_count: int = Field(default=0, ge=0, le=12)
    tier: str | None = None


@router.get("/draft-backups")
async def list_draft_backups(user: User = Depends(get_current_db_user)):
    """Список облачных черновиков TTL 7 дней §3.3.2."""
    from app.services import draft_backup as dbk

    return {"items": dbk.list_backups(user.id), "ttl_days": dbk.TTL_DAYS}


@router.post("/draft-backups/prepare")
async def prepare_draft_backup(
    body: DraftBackupPrepareBody,
    user: User = Depends(get_current_db_user),
):
    """Presigned upload ZIP черновика."""
    from app.services import draft_backup as dbk

    return dbk.prepare_upload(
        user.id,
        body.model_uuid,
        metadata={
            "category": body.category,
            "captured_count": body.captured_count,
            "tier": body.tier,
        },
    )


@router.get("/draft-backups/{model_uuid}/restore")
async def restore_draft_backup(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
):
    """Presigned download для восстановления черновика §3.3.2."""
    from app.services import draft_backup as dbk

    return dbk.restore_download(user.id, model_uuid)


class AnalyticsEventsBody(BaseModel):
    events: list[dict] = Field(default_factory=list, max_length=200)


@router.post("/analytics/events")
async def post_analytics_events(
    body: AnalyticsEventsBody,
    user: User = Depends(get_current_db_user),
):
    """Приём пакета аналитики с мобильного клиента §19.20."""
    return {"accepted": len(body.events), "user_id": user.id}


@router.get("/campaign_banners")
async def list_campaign_banners(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Баннеры из неиспользованных CampaignEntitlement."""
    from app.models import Campaign, CampaignEntitlement, Promocode

    ents = (
        await db.scalars(
            select(CampaignEntitlement)
            .where(
                CampaignEntitlement.user_id == user.id,
                CampaignEntitlement.consumed_at.is_(None),
            )
            .order_by(CampaignEntitlement.created_at.desc())
        )
    ).all()
    items: list[dict] = []
    for ent in ents:
        camp = await db.get(Campaign, ent.campaign_id)
        if not camp or camp.status != "running":
            continue
        meta = dict(ent.meta or {})
        cfg = dict(camp.config or {})
        title = str(meta.get("banner_title") or cfg.get("banner_title") or camp.name)
        body_text = str(meta.get("banner_body") or cfg.get("banner_body") or "")
        if not body_text and meta.get("issued_code"):
            body_text = str(meta["issued_code"])
        elif ent.promocode_id and not body_text:
            promo = await db.get(Promocode, ent.promocode_id)
            if promo and meta.get("issued_code"):
                body_text = str(meta["issued_code"])
        items.append(
            {
                "id": ent.id,
                "campaign_id": ent.campaign_id,
                "kind": ent.kind,
                "title": title,
                "body": body_text,
            }
        )
    return {"items": items}
