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
