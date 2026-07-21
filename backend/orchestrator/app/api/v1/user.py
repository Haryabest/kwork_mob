"""Пользователь: профиль, баланс, транзакции, модели, device tokens."""

from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user
from app.models import DeviceToken, Model3D, Order, Transaction, User
from app.schemas.auth import AccountTypeRequest
from app.schemas.analytics import AnalyticsEventsBody
from app.schemas.balance_filters import (
    BalanceFilterPresetBody,
    BalanceFiltersBody,
)
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
    from app.services import user_avatar as av_svc
    from app.services.locale import normalize_locale

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
        "avatar_url": av_svc.presigned_avatar_url(getattr(user, "avatar_key", None)),
        "preferred_locale": normalize_locale(getattr(user, "preferred_locale", None)),
        "gender": getattr(user, "gender", None),
        "region": getattr(user, "region", None),
        "card_bank_issuer": getattr(user, "card_bank_issuer", None),
    }


@router.get("/me")
async def get_me(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Текущий пользователь (для seller и staff)."""
    from app.services import oauth_auth as oauth_svc

    payload = _user_payload(user)
    identities = await oauth_svc.list_oauth_identities(db, user.id)
    payload["oauth_providers"] = [row["provider"] for row in identities if row.get("provider")]
    return payload


@router.get("/audit")
async def user_audit_log(
    action: str | None = Query(None),
    action_prefix: str | None = Query(None, description="Например oauth_"),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Личный audit_log текущего пользователя §2.5.5."""
    from app.services import audit_query as aq

    return await aq.list_audit_logs(
        db,
        action=action,
        action_prefix=action_prefix,
        user_id=user.id,
        days=days,
        limit=limit,
        offset=offset,
    )


@router.get("/audit/export")
async def user_audit_export(
    action: str | None = Query(None),
    action_prefix: str | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """CSV export личного audit_log §2.5.5."""
    import csv
    import io

    from fastapi.responses import Response

    from app.services import audit_query as aq

    data = await aq.list_audit_logs(
        db,
        action=action,
        action_prefix=action_prefix,
        user_id=user.id,
        days=days,
        limit=5000,
        offset=0,
    )
    rows = data["items"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "user_id", "action", "details", "created_at"])
    for r in rows:
        w.writerow([r["id"], r["user_id"], r["action"], r["details"], r["created_at"] or ""])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="user_audit.csv"'},
    )


@router.get("/access-log")
async def user_access_log(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Личные скачивания моделей §2.5.5 / §10.7.2."""
    from app.services import access_log as access_svc

    return await access_svc.list_access_logs(db, user_id=user.id, limit=limit)


@router.get("/access-log/export")
async def user_access_log_export(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """CSV export личных скачиваний §2.5.5."""
    from fastapi.responses import Response

    from app.services import access_log as access_svc

    data = await access_svc.list_access_logs(db, user_id=user.id, limit=5000)
    return Response(
        content=access_svc.to_csv(data["items"]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="user-access-log.csv"'},
    )


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
    if "preferred_locale" in payload:
        from app.services.locale import normalize_locale

        user.preferred_locale = normalize_locale(str(payload["preferred_locale"]))
    if "gender" in payload:
        from app.services.marketing_profile import normalize_gender

        if user.marketing_opt_in:
            user.gender = normalize_gender(str(payload["gender"]) if payload["gender"] is not None else None)
    if "region" in payload and payload["region"] is not None:
        user.region = str(payload["region"]).strip()[:128] or None
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


@router.post("/me/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Загрузка аватара §20.8.1 (JPG/PNG/WebP, до 2 МБ)."""
    from app.services import user_avatar as av_svc

    result = await av_svc.upload_avatar(db, user=user, file=file)
    await db.commit()
    await db.refresh(user)
    return {**result, **_user_payload(user)}


@router.delete("/me/avatar")
async def delete_my_avatar(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить аватар §20.8.1."""
    from app.services import user_avatar as av_svc

    await av_svc.delete_avatar(db, user=user)
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


@router.get("/balance-filter-presets")
async def get_balance_filter_presets(user: User = Depends(get_current_db_user)):
    """Named saved views for personal balance filters §20.3.4."""
    from app.services import balance_filters as bf

    return {"scope": "personal", "items": bf.list_presets(user)}


@router.post("/balance-filter-presets")
async def create_balance_filter_preset(
    body: BalanceFilterPresetBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import balance_filters as bf

    try:
        row = await bf.upsert_preset(db, user, name=body.name, filters=body.model_dump())
    except ValueError as exc:
        if str(exc) == "limit":
            raise HTTPException(400, "Максимум 10 сохранённых представлений") from exc
        raise HTTPException(400, "Укажите название") from exc
    await db.commit()
    return {"scope": "personal", "preset": row}


@router.delete("/balance-filter-presets/{preset_id}")
async def delete_balance_filter_preset(
    preset_id: str,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services import balance_filters as bf

    ok = await bf.delete_preset(db, user, preset_id=preset_id)
    if not ok:
        raise HTTPException(404, "Представление не найдено")
    await db.commit()
    return {"ok": True}


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
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Пополнение: карта (redirect) или СБП QR + фискальный чек (§8.12 / §8.6.4)."""
    from app.core.config import settings
    from app.services import marketing_profile as mp_svc
    from app.services.tax import build_receipt_for_payment
    from app.services.yookassa import yookassa_service

    mp_svc.apply_region_from_request(user, request, force=True)

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
    try:
        from app.core.redis import get_redis
        from app.services import push_fallback

        redis = await get_redis()
        await push_fallback.cancel_for_notification(
            redis, user_id=user.id, notif_id=notification_id
        )
    except Exception:
        pass
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


@router.get("/me/deletion-request")
async def get_deletion_request(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Статус заявки на удаление аккаунта (§20.8)."""
    from sqlalchemy import select

    from app.models import DeletionRequest

    row = await db.scalar(
        select(DeletionRequest)
        .where(
            DeletionRequest.user_id == user.id,
            DeletionRequest.status.in_(("pending", "processing")),
        )
        .order_by(DeletionRequest.requested_at.desc())
    )
    if not row:
        return {"active": False}
    return {
        "active": True,
        "id": row.id,
        "status": row.status,
        "requested_at": row.requested_at.isoformat() if row.requested_at else None,
        "due_at": row.due_at.isoformat() if row.due_at else None,
    }


@router.get("/models")
async def list_user_models(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
    company_id: int | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    date_from: str | None = Query(default=None, max_length=10),
    date_to: str | None = Query(default=None, max_length=10),
    tier: str | None = Query(default=None, pattern=r"^(small|large)$"),
    author_id: int | None = Query(default=None, ge=1),
    category: str | None = Query(default=None, max_length=32),
    publish_filter: str | None = Query(default=None, pattern=r"^(published|draft)$"),
    sort: str = Query(default="newest", pattern=r"^(newest|oldest)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    from app.services import model_storage as ms
    from app.services.access import assert_company_access

    if company_id is not None:
        await assert_company_access(db, user, company_id)
        where = [Model3D.company_id == company_id, Model3D.trashed_at.is_(None)]
    else:
        where = [Model3D.user_id == user.id, Model3D.trashed_at.is_(None)]

    if search and search.strip():
        q = f"%{search.strip()}%"
        where.append(or_(Model3D.display_name.ilike(q), Model3D.uuid.ilike(q)))

    if date_from:
        try:
            d0 = date.fromisoformat(date_from)
            where.append(Model3D.created_at >= datetime.combine(d0, time.min, tzinfo=timezone.utc))
        except ValueError:
            raise HTTPException(400, "Некорректная date_from")

    if date_to:
        try:
            d1 = date.fromisoformat(date_to)
            where.append(Model3D.created_at <= datetime.combine(d1, time.max, tzinfo=timezone.utc))
        except ValueError:
            raise HTTPException(400, "Некорректная date_to")

    if tier:
        where.append(Order.tier == tier)

    if author_id is not None:
        where.append(Model3D.user_id == author_id)

    if category:
        where.append(Order.category == category)

    if publish_filter == "published":
        where.append(
            or_(
                Model3D.publish_status.ilike("%published%"),
                Model3D.publish_status.ilike("%verified%"),
            )
        )
    elif publish_filter == "draft":
        where.append(
            or_(
                Model3D.publish_status.is_(None),
                Model3D.publish_status.in_(["", "none", "not_published"]),
            )
        )

    base = (
        select(Model3D, Order.category, Order.tier, Order.status)
        .outerjoin(Order, Model3D.order_id == Order.id)
        .where(*where)
    )

    total = await db.scalar(
        select(func.count(Model3D.id))
        .select_from(Model3D)
        .outerjoin(Order, Model3D.order_id == Order.id)
        .where(*where)
    ) or 0

    order = Model3D.id.desc() if sort == "newest" else Model3D.id.asc()
    rows = (await db.execute(base.order_by(order).offset(offset).limit(limit))).all()

    return {
        "items": [
            {
                "uuid": m.uuid,
                "order_id": m.order_id,
                "display_name": m.display_name,
                "user_id": m.user_id,
                "category": cat,
                "tier": order_tier,
                "glb_url": m.glb_url,
                "usdz_url": m.usdz_url,
                "publish_status": m.publish_status,
                "order_status": order_status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "storage": ms.storage_meta(m),
            }
            for m, cat, order_tier, order_status in rows
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "scope": "company" if company_id else "personal",
    }


@router.get("/devices")
async def list_devices(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Зарегистрированные push-устройства §3.4.3."""
    rows = (
        await db.scalars(
            select(DeviceToken).where(DeviceToken.user_id == user.id).order_by(DeviceToken.id.desc()).limit(50)
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "platform": r.platform,
                "app_version": r.app_version,
                "token_prefix": (r.token[:12] + "…") if len(r.token) > 12 else r.token,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    }


@router.delete("/devices/{device_id}")
async def delete_device_by_id(
    device_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Отвязка push-устройства по id §2.5.5."""
    row = await db.scalar(
        select(DeviceToken).where(DeviceToken.id == device_id, DeviceToken.user_id == user.id)
    )
    if not row:
        raise HTTPException(404, "Устройство не найдено")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


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


@router.delete("/draft-backups/{model_uuid}")
async def delete_draft_backup(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
):
    """Удаление облачного черновика §3.3.2."""
    from app.services import draft_backup as dbk

    return dbk.delete_backup(user.id, model_uuid)


@router.get("/draft-backups/{model_uuid}/restore")
async def restore_draft_backup(
    model_uuid: str,
    user: User = Depends(get_current_db_user),
):
    """Presigned download для восстановления черновика §3.3.2."""
    from app.services import draft_backup as dbk

    return dbk.restore_download(user.id, model_uuid)


@router.post("/analytics/events")
async def post_analytics_events(
    body: AnalyticsEventsBody,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Приём пакета аналитики с мобильного клиента §19.20."""
    from app.services import analytics_ingest as ai

    accepted = await ai.persist_events(db, user, body.events)
    await db.commit()
    try:
        from app.services.analytics_query import clickhouse_health

        ch_health = clickhouse_health()
    except Exception:
        ch_health = {"ok": False}
    return {
        "accepted": accepted,
        "user_id": user.id,
        "clickhouse_ok": bool(ch_health.get("ok")),
    }


@router.get("/campaign_banners")
async def list_campaign_banners(
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Баннеры из неиспользованных CampaignEntitlement."""
    from app.models import Campaign, CampaignEntitlement, Promocode
    from app.services import campaigns as camp_svc

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
                "click_url": camp_svc.click_track_url(
                    ent.campaign_id,
                    target_url=cfg.get("banner_cta_url") or cfg.get("cta_url"),
                    user_id=user.id,
                ),
            }
        )
    return {"items": items}
