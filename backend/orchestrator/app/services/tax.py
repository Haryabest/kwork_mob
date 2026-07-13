"""Налоговый модуль §8.6: реквизиты + PDF счёт/акт + Excel выгрузка."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OwnerTaxSettings, Transaction, User

MODES = ("self_employed", "ip", "ooo")


async def get_settings(db: AsyncSession) -> OwnerTaxSettings:
    row = await db.get(OwnerTaxSettings, 1)
    if not row:
        row = OwnerTaxSettings(id=1, mode="self_employed", vat_rate=0)
        db.add(row)
        await db.flush()
    return row


async def update_settings(db: AsyncSession, data: dict[str, Any]) -> OwnerTaxSettings:
    row = await get_settings(db)
    mode = data.get("mode", row.mode)
    if mode not in MODES:
        raise HTTPException(400, f"mode: {', '.join(MODES)}")
    row.mode = mode
    for field in (
        "full_name",
        "inn",
        "phone",
        "ogrnip",
        "ogrn",
        "kpp",
        "org_name",
        "legal_address",
        "bank_name",
        "bank_bik",
        "bank_account",
    ):
        if field in data:
            setattr(row, field, data[field])
    if "vat_rate" in data:
        vat = int(data["vat_rate"] or 0)
        if vat not in (0, 20):
            raise HTTPException(400, "vat_rate: 0 или 20")
        if mode == "self_employed":
            vat = 0
        row.vat_rate = vat
    row.updated_at = datetime.now(timezone.utc)
    # валидация по режиму
    if mode == "self_employed" and not row.inn:
        raise HTTPException(400, "Для самозанятого укажите ИНН")
    if mode == "ip" and not (row.inn and row.ogrnip):
        raise HTTPException(400, "Для ИП нужны ИНН и ОГРНИП")
    if mode == "ooo" and not (row.inn and row.kpp and row.ogrn and row.org_name):
        raise HTTPException(400, "Для ООО нужны ИНН, КПП, ОГРН, наименование")
    await db.flush()
    return row


def settings_public(row: OwnerTaxSettings) -> dict:
    # УСН = ИП/ООО без НДС; ОСНО = с НДС 20% (§8.6)
    tax_system = "npd"
    if row.mode == "self_employed":
        tax_system = "npd"
    elif int(row.vat_rate or 0) == 20:
        tax_system = "osno"
    else:
        tax_system = "usn"
    return {
        "mode": row.mode,
        "tax_system": tax_system,
        "full_name": row.full_name,
        "inn": row.inn,
        "phone": row.phone,
        "ogrnip": row.ogrnip,
        "ogrn": row.ogrn,
        "kpp": row.kpp,
        "org_name": row.org_name,
        "legal_address": row.legal_address,
        "bank_name": row.bank_name,
        "bank_bik": row.bank_bik,
        "bank_account": row.bank_account,
        "vat_rate": row.vat_rate,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def yookassa_vat_code(tax: OwnerTaxSettings) -> int:
    """Коды НДС ЮKassa: 1=без НДС, 4=20%."""
    if tax.mode == "self_employed" or int(tax.vat_rate or 0) == 0:
        return 1
    return 4


def build_yookassa_receipt(
    *,
    tax: OwnerTaxSettings,
    customer_email: str,
    description: str,
    amount_rub: int,
    customer_name: str | None = None,
) -> dict[str, Any]:
    """Чек 54-ФЗ через ЮKassa (§2.9 / §8.6.4). Без «Мой налог»."""
    email = (customer_email or "").strip() or "noreply@kworkmob.local"
    customer: dict[str, Any] = {"email": email}
    # ФИО опционально; иначе «Клиент» (§2.10)
    name = (customer_name or "").strip() or "Клиент"
    customer["full_name"] = name[:256]
    return {
        "customer": customer,
        "items": [
            {
                "description": (description or "Услуга KWork Mob")[:128],
                "quantity": "1.00",
                "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
                "vat_code": yookassa_vat_code(tax),
                "payment_mode": "full_payment",
                "payment_subject": "service",
            }
        ],
    }


async def build_receipt_for_payment(
    db: AsyncSession,
    *,
    customer_email: str,
    description: str,
    amount_rub: int,
    customer_name: str | None = None,
) -> dict[str, Any]:
    tax = await get_settings(db)
    return build_yookassa_receipt(
        tax=tax,
        customer_email=customer_email,
        description=description,
        amount_rub=amount_rub,
        customer_name=customer_name,
    )


def _seller_line(tax: OwnerTaxSettings) -> str:
    if tax.mode == "ooo":
        return f"{tax.org_name or 'ООО'}, ИНН {tax.inn}, КПП {tax.kpp}, ОГРН {tax.ogrn}"
    if tax.mode == "ip":
        return f"ИП {tax.full_name or ''}, ИНН {tax.inn}, ОГРНИП {tax.ogrnip}"
    return f"Самозанятый {tax.full_name or ''}, ИНН {tax.inn} (НПД)"


def build_invoice_pdf(
    *,
    tax: OwnerTaxSettings,
    order: Order,
    buyer_email: str,
    doc_type: str = "invoice",
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 50
    title = "СЧЁТ НА ОПЛАТУ" if doc_type == "invoice" else "АКТ ВЫПОЛНЕННЫХ УСЛУГ"
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, title)
    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"№ {order.id} от {order.created_at.strftime('%d.%m.%Y') if order.created_at else '—'}")
    y -= 20
    c.drawString(50, y, f"Исполнитель: {_seller_line(tax)}")
    y -= 16
    if tax.legal_address:
        c.drawString(50, y, f"Адрес: {tax.legal_address[:90]}")
        y -= 16
    if tax.bank_account:
        c.drawString(50, y, f"Р/с {tax.bank_account} БИК {tax.bank_bik or ''} {tax.bank_name or ''}")
        y -= 16
    c.drawString(50, y, f"Заказчик: {buyer_email}")
    y -= 24
    base = order.amount_original or order.amount
    upsell = order.upsell_amount or 0
    discount = order.discount_amount or 0
    net = order.amount
    vat = 0
    if tax.mode != "self_employed" and tax.vat_rate:
        # сумма в заказе без НДС по ТЗ; НДС сверху для счёта
        vat = int(round(net * tax.vat_rate / 100))
    total = net + vat
    lines = [
        f"Услуга: генерация 3D-модели (тариф {order.tier})",
        f"База: {base} руб.",
        f"Апсейлы: {upsell} руб.",
        f"Скидка: {discount} руб.",
        f"К оплате без НДС: {net} руб.",
    ]
    if vat:
        lines.append(f"НДС {tax.vat_rate}%: {vat} руб.")
        lines.append(f"Итого с НДС: {total} руб.")
    else:
        lines.append(f"НДС не облагается (режим {tax.mode}). Итого: {total} руб.")
    for line in lines:
        c.drawString(50, y, line)
        y -= 16
    if doc_type == "act":
        y -= 10
        c.drawString(50, y, "Услуги оказаны полностью. Претензий по объёму и качеству нет.")
        y -= 30
        c.drawString(50, y, "Исполнитель _____________    Заказчик _____________")
    c.showPage()
    c.save()
    return buf.getvalue()


async def export_transactions_xlsx(
    db: AsyncSession,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
) -> bytes:
    from openpyxl import Workbook

    q = select(Transaction).order_by(Transaction.id.desc()).limit(5000)
    if date_from:
        q = q.where(Transaction.created_at >= date_from)
    if date_to:
        q = q.where(Transaction.created_at <= date_to)
    rows = (await db.scalars(q)).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "transactions"
    ws.append(["id", "user_id", "company_id", "amount", "type", "description", "external_id", "created_at"])
    for t in rows:
        ws.append(
            [
                t.id,
                t.user_id,
                t.company_id,
                t.amount,
                t.tx_type,
                t.description,
                t.external_id,
                t.created_at.isoformat() if t.created_at else None,
            ]
        )
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


async def invoice_for_order(db: AsyncSession, order_id: int, user: User, doc_type: str) -> bytes:
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        # admin/owner сервиса тоже может — упрощённо: владелец заказа или staff
        if not order:
            raise HTTPException(404, "Заказ не найден")
        if order.user_id != user.id and not user.staff_role:
            raise HTTPException(403, "Нет доступа")
    tax = await get_settings(db)
    buyer = await db.get(User, order.user_id)
    return build_invoice_pdf(
        tax=tax,
        order=order,
        buyer_email=buyer.email if buyer else str(order.user_id),
        doc_type=doc_type,
    )
