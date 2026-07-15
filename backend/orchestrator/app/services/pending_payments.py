"""Pending YooKassa topups до webhook §20.3.4."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BalancePendingPayment, Transaction
from app.services.company_balance import TX_STATUS_LABELS


def _channel_label(method: str) -> str:
    return "СБП" if method in ("sbp_qr", "sbp") else "ЮKassa"


def pending_status_label(status: str) -> str:
    if status == "pending":
        return TX_STATUS_LABELS["pending"]
    if status in ("canceled", "failed"):
        return TX_STATUS_LABELS["failed"]
    return TX_STATUS_LABELS["succeeded"]


def pending_to_dict(p: BalancePendingPayment) -> dict:
    company_suffix = " компании" if p.company_id else ""
    channel = _channel_label(p.payment_method or "redirect")
    st = "pending" if p.status == "pending" else ("failed" if p.status in ("canceled", "failed") else "succeeded")
    return {
        "id": f"pending:{p.payment_id}",
        "payment_id": p.payment_id,
        "amount": p.amount,
        "type": "topup",
        "description": f"Пополнение{company_suffix} через {channel}",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "status": st,
        "status_label": pending_status_label(p.status),
        "pending": True,
        "user_id": p.user_id,
        "company_id": p.company_id,
    }


async def upsert_pending(
    db: AsyncSession,
    *,
    payment_id: str,
    user_id: int,
    amount: int,
    payment_method: str,
    purpose: str = "topup",
    company_id: int | None = None,
) -> BalancePendingPayment:
    row = await db.scalar(select(BalancePendingPayment).where(BalancePendingPayment.payment_id == payment_id))
    if row:
        return row
    row = BalancePendingPayment(
        payment_id=payment_id,
        user_id=user_id,
        company_id=company_id,
        amount=amount,
        payment_method=payment_method,
        purpose=purpose,
        status="pending",
    )
    db.add(row)
    await db.flush()
    return row


async def mark_status(db: AsyncSession, payment_id: str, status: str) -> None:
    row = await db.scalar(select(BalancePendingPayment).where(BalancePendingPayment.payment_id == payment_id))
    if not row:
        return
    row.status = status
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()


def _pending_stmt(
    *,
    user_id: int | None = None,
    company_id: int | None = None,
    personal_only: bool = False,
    date_from: date | None = None,
    date_to: date | None = None,
):
    stmt = select(BalancePendingPayment)
    if user_id is not None:
        stmt = stmt.where(BalancePendingPayment.user_id == user_id)
    if company_id is not None:
        stmt = stmt.where(BalancePendingPayment.company_id == company_id)
    elif personal_only:
        stmt = stmt.where(BalancePendingPayment.company_id.is_(None))
    stmt = stmt.where(BalancePendingPayment.status.in_(("pending", "canceled", "failed")))
    if date_from is not None:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        stmt = stmt.where(BalancePendingPayment.created_at >= start)
    if date_to is not None:
        end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(BalancePendingPayment.created_at <= end)
    return stmt.order_by(BalancePendingPayment.id.desc())


async def _without_settled_tx(db: AsyncSession, rows: list[BalancePendingPayment]) -> list[BalancePendingPayment]:
    if not rows:
        return []
    ids = [r.payment_id for r in rows]
    settled = set(
        await db.scalars(select(Transaction.external_id).where(Transaction.external_id.in_(ids)))
    )
    return [r for r in rows if r.payment_id not in settled]


async def list_pending_dicts(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    company_id: int | None = None,
    personal_only: bool = False,
    date_from: date | None = None,
    date_to: date | None = None,
    tx_type: str | None = None,
) -> list[dict]:
    if tx_type and tx_type not in ("all", "topup"):
        return []
    stmt = _pending_stmt(
        user_id=user_id,
        company_id=company_id,
        personal_only=personal_only,
        date_from=date_from,
        date_to=date_to,
    )
    rows = (await db.scalars(stmt)).all()
    rows = await _without_settled_tx(db, rows)
    return [pending_to_dict(r) for r in rows]


def merge_transaction_page(
    *,
    tx_items: list[dict],
    pending_items: list[dict],
    tx_total: int,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    """Pending сверху первой страницы, total = tx_total + len(pending)."""
    pending_count = len(pending_items)
    total = tx_total + pending_count
    page: list[dict] = []

    if offset < pending_count:
        page.extend(pending_items[offset : offset + limit])
        need = limit - len(page)
        if need > 0:
            page.extend(tx_items[:need])
    else:
        page = tx_items

    return page, total


async def notify_topup_failed(db: AsyncSession, payment_id: str) -> None:
    """Push Owner при payment.failed для пополнения §8."""
    from app.models import Company
    from app.services import push as push_svc

    row = await db.scalar(
        select(BalancePendingPayment).where(BalancePendingPayment.payment_id == payment_id)
    )
    if not row:
        return
    owner_id = row.user_id
    if row.company_id:
        company = await db.get(Company, row.company_id)
        if company:
            owner_id = company.owner_id
        title = "Ошибка пополнения компании"
        body = (
            f"Платёж на {row.amount} ₽ не прошёл. "
            "Попробуйте снова или обратитесь в поддержку."
        )
    else:
        title = "Ошибка пополнения"
        body = f"Платёж на {row.amount} ₽ не прошёл."
    from app.models import User

    owner = await db.get(User, owner_id)
    if owner and not push_svc.user_wants_notification(owner, "topup_failed"):
        return
    await push_svc.send_to_user(
        db,
        owner_id,
        title,
        body,
        data={
            "type": "topup_failed",
            "payment_id": payment_id,
            "company_id": str(row.company_id) if row.company_id else "",
            "dedup_key": f"topup_failed:{payment_id}",
            "deeplink": "/home/balance",
        },
    )


async def settle_succeeded_topup(db: AsyncSession, payment: dict) -> str:
    """Зачислить succeeded topup из ответа YooKassa (poll / Celery §8)."""
    from app.models import Company, Transaction, User
    from app.services.task_lifecycle import try_queue_awaiting_orders

    payment_id = str(payment.get("id") or "")
    if not payment_id:
        return "skipped"
    meta = payment.get("metadata") or {}
    purpose = str(meta.get("purpose") or "topup")
    if purpose not in ("topup", "company_topup"):
        return "skipped"
    user_id = int(meta.get("user_id") or 0)
    amount = int(float((payment.get("amount") or {}).get("value") or 0))
    if not user_id or amount <= 0:
        return "skipped"

    existing = await db.scalar(select(Transaction).where(Transaction.external_id == payment_id))
    if existing:
        await mark_status(db, payment_id, "succeeded")
        return "exists"

    user = await db.get(User, user_id)
    if not user:
        return "skipped"

    method = str(meta.get("payment_method") or "redirect")
    channel = _channel_label(method)

    if purpose == "company_topup":
        company_id = int(meta.get("company_id") or 0)
        company = await db.get(Company, company_id) if company_id else None
        if not company:
            return "skipped"
        company.balance += amount
        db.add(
            Transaction(
                user_id=user.id,
                company_id=company.id,
                amount=amount,
                tx_type="topup",
                description=f"Пополнение баланса компании через {channel}",
                external_id=payment_id,
            )
        )
    else:
        user.balance += amount
        db.add(
            Transaction(
                user_id=user.id,
                amount=amount,
                tx_type="topup",
                description=f"Пополнение через {channel}",
                external_id=payment_id,
            )
        )
        await db.flush()
        await try_queue_awaiting_orders(db, user.id)

    await mark_status(db, payment_id, "succeeded")
    return "settled"


async def refresh_stale_waiting_capture(
    db: AsyncSession,
    *,
    min_age_minutes: int = 5,
) -> dict[str, int]:
    """Celery: re-check pending payments старше N минут через YooKassa API §8."""
    from datetime import timedelta

    from app.services.yookassa import yookassa_service

    if not yookassa_service.configured:
        return {"checked": 0, "settled": 0, "failed": 0, "still_pending": 0, "skipped": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=min_age_minutes)
    rows = (
        await db.scalars(
            select(BalancePendingPayment)
            .where(
                BalancePendingPayment.status == "pending",
                BalancePendingPayment.created_at <= cutoff,
            )
            .order_by(BalancePendingPayment.id.asc())
            .limit(50)
        )
    ).all()

    checked = settled = failed = still_pending = skipped = 0
    for row in rows:
        checked += 1
        try:
            payment = await yookassa_service.get_payment(row.payment_id)
        except Exception:  # noqa: BLE001
            skipped += 1
            continue
        status = str(payment.get("status") or "pending")
        if status == "succeeded":
            result = await settle_succeeded_topup(db, payment)
            if result in ("settled", "exists"):
                settled += 1
            else:
                skipped += 1
        elif status in ("canceled", "failed"):
            await mark_status(db, row.payment_id, "failed" if status == "failed" else "canceled")
            failed += 1
        elif status == "waiting_for_capture":
            still_pending += 1
            row.updated_at = datetime.now(timezone.utc)
            await db.flush()
        else:
            still_pending += 1

    return {
        "checked": checked,
        "settled": settled,
        "failed": failed,
        "still_pending": still_pending,
        "skipped": skipped,
    }


async def purge_old_settled(db: AsyncSession, *, days: int = 30) -> int:
    """Удалить settled pending payments старше N дней (Celery §20.3.4)."""
    from datetime import timedelta

    from sqlalchemy import delete

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        delete(BalancePendingPayment).where(
            BalancePendingPayment.status.in_(("succeeded", "canceled", "failed")),
            BalancePendingPayment.updated_at < cutoff,
        )
    )
    await db.flush()
    return int(result.rowcount or 0)
