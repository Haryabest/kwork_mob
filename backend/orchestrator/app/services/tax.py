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
from app.services import pii as pii_svc

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
            pii_svc.encrypt_tax_fields(row, {field: data[field]})
    if "vat_rate" in data:
        vat = int(data["vat_rate"] or 0)
        if vat not in (0, 20):
            raise HTTPException(400, "vat_rate: 0 или 20")
        if mode == "self_employed":
            vat = 0
        row.vat_rate = vat
    row.updated_at = datetime.now(timezone.utc)
    plain = pii_svc.tax_row_plain(row)
    if mode == "self_employed" and not plain["inn"]:
        raise HTTPException(400, "Для самозанятого укажите ИНН")
    if mode == "ip" and not (plain["inn"] and plain["ogrnip"]):
        raise HTTPException(400, "Для ИП нужны ИНН и ОГРНИП")
    if mode == "ooo" and not (plain["inn"] and plain["kpp"] and plain["ogrn"] and plain["org_name"]):
        raise HTTPException(400, "Для ООО нужны ИНН, КПП, ОГРН, наименование")
    await db.flush()
    return row


def settings_public(row: OwnerTaxSettings) -> dict:
    plain = pii_svc.tax_row_plain(row)
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
        **plain,
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
    plain = pii_svc.tax_row_plain(tax)
    if tax.mode == "ooo":
        return (
            f"{plain['org_name'] or 'ООО'}, ИНН {plain['inn']}, "
            f"КПП {plain['kpp']}, ОГРН {plain['ogrn']}"
        )
    if tax.mode == "ip":
        return f"ИП {plain['full_name'] or ''}, ИНН {plain['inn']}, ОГРНИП {plain['ogrnip']}"
    return f"Самозанятый {plain['full_name'] or ''}, ИНН {plain['inn']} (НПД)"


def _draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, max_chars: int = 95) -> float:
    """Рисует строку с переносом; возвращает новый y."""
    t = text or ""
    while t:
        chunk, t = t[:max_chars], t[max_chars:]
        c.drawString(x, y, chunk)
        y -= 14
    return y


def build_invoice_pdf(
    *,
    tax: OwnerTaxSettings,
    order: Order,
    buyer_email: str,
    doc_type: str = "invoice",
    buyer_name: str | None = None,
    buyer_inn: str | None = None,
) -> bytes:
    """Счёт/акт PDF §8.6 — шапка, реквизиты, таблица услуг, НДС, подписи."""
    from reportlab.lib.units import mm

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    left, right = 20 * mm, w - 20 * mm
    y = h - 18 * mm

    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(0.0, 0.34, 0.72)
    c.drawString(left, y, "3dvektor")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 8)
    c.drawRightString(right, y, "Документ сформирован автоматически")
    y -= 8
    c.setStrokeColorRGB(0.0, 0.34, 0.72)
    c.setLineWidth(1.2)
    c.line(left, y, right, y)
    y -= 22

    title = "СЧЁТ НА ОПЛАТУ" if doc_type == "invoice" else "АКТ ВЫПОЛНЕННЫХ УСЛУГ"
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left, y, title)
    y -= 18
    doc_date = order.created_at.strftime("%d.%m.%Y") if order.created_at else "—"
    c.setFont("Helvetica", 10)
    c.drawString(left, y, f"№ {order.id} от {doc_date}")
    y -= 8
    c.setStrokeColorRGB(0.85, 0.85, 0.88)
    c.setLineWidth(0.5)
    c.line(left, y, right, y)
    y -= 18

    plain = pii_svc.tax_row_plain(tax)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "Исполнитель")
    y -= 14
    c.setFont("Helvetica", 9)
    y = _draw_wrapped(c, _seller_line(tax), left, y, 100)
    if plain.get("legal_address"):
        y = _draw_wrapped(c, f"Адрес: {plain['legal_address']}", left, y, 100)
    if plain.get("bank_account"):
        bank = (
            f"р/с {plain['bank_account']}, БИК {plain.get('bank_bik') or '—'}, "
            f"{plain.get('bank_name') or ''}"
        ).strip()
        y = _draw_wrapped(c, bank, left, y, 100)
    y -= 6

    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "Заказчик")
    y -= 14
    c.setFont("Helvetica", 9)
    buyer_line = buyer_name or buyer_email or "—"
    if buyer_inn:
        buyer_line = f"{buyer_line}, ИНН {buyer_inn}"
    y = _draw_wrapped(c, buyer_line, left, y, 100)
    if buyer_email and buyer_name:
        y = _draw_wrapped(c, f"Email: {buyer_email}", left, y, 100)
    y -= 10

    base = int(order.amount_original or order.amount or 0)
    upsell = int(order.upsell_amount or 0)
    discount = int(order.discount_amount or 0)
    net = int(order.amount or 0)
    vat = 0
    if tax.mode != "self_employed" and tax.vat_rate:
        vat = int(round(net * tax.vat_rate / 100))
    total = net + vat

    # таблица услуг (§8 — перечисление опций)
    col_n, col_name, col_qty, col_price, col_sum = left, left + 22, right - 120, right - 70, right
    row_h = 16
    c.setFillColorRGB(0.94, 0.95, 0.98)
    c.rect(left, y - 4, right - left, row_h + 2, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col_n, y, "№")
    c.drawString(col_name, y, "Наименование")
    c.drawRightString(col_qty, y, "Кол-во")
    c.drawRightString(col_price, y, "Цена, руб")
    c.drawRightString(col_sum, y, "Сумма")
    y -= row_h

    items: list[tuple[str, int]] = [
        (f"Генерация 3D-модели, тариф {order.tier}", base),
    ]
    upsell_opts = order.upsell_options or []
    if isinstance(upsell_opts, list) and upsell_opts and upsell:
        share = upsell // max(len(upsell_opts), 1)
        rem = upsell - share * len(upsell_opts)
        for i, code in enumerate(upsell_opts):
            amt = share + (rem if i == 0 else 0)
            items.append((f"Опция: {code}", amt))
    elif upsell:
        items.append(("Апсейл-опции", upsell))
    if discount:
        items.append(("Скидка / промокод", -discount))

    c.setFont("Helvetica", 8)
    for idx, (name, amount) in enumerate(items, start=1):
        if y < 60 * mm:
            c.showPage()
            y = h - 20 * mm
        c.drawString(col_n, y, str(idx))
        c.drawString(col_name, y, name[:55])
        c.drawRightString(col_qty, y, "1")
        c.drawRightString(col_price, y, f"{amount:,}".replace(",", " "))
        c.drawRightString(col_sum, y, f"{amount:,}".replace(",", " "))
        y -= row_h

    y -= 6
    c.setStrokeColorRGB(0.75, 0.75, 0.78)
    c.line(left, y + 10, right, y + 10)
    c.setFont("Helvetica", 9)
    c.drawRightString(col_price, y, "Без НДС:")
    c.drawRightString(col_sum, y, f"{net:,} руб.".replace(",", " "))
    y -= 14
    if vat:
        c.drawRightString(col_price, y, f"НДС {tax.vat_rate}%:")
        c.drawRightString(col_sum, y, f"{vat:,} руб.".replace(",", " "))
        y -= 14
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(col_price, y, "Итого с НДС:")
        c.drawRightString(col_sum, y, f"{total:,} руб.".replace(",", " "))
    else:
        c.setFont("Helvetica", 8)
        c.drawString(left, y, f"НДС не облагается (режим {tax.mode})")
        y -= 14
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(col_price, y, "Итого:")
        c.drawRightString(col_sum, y, f"{total:,} руб.".replace(",", " "))
    y -= 24

    if doc_type == "act":
        c.setFont("Helvetica", 9)
        y = _draw_wrapped(
            c,
            "Услуги оказаны полностью. Претензий по объёму, срокам и качеству нет.",
            left,
            y,
            95,
        )
        y -= 16
        c.drawString(left, y, "Исполнитель _________________ / ___________ /")
        y -= 18
        c.drawString(left, y, "Заказчик _________________ / ___________ /")
        y -= 20

    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.4, 0.4, 0.45)
    c.drawString(
        left,
        12 * mm,
        f"order_id={order.id} task={order.task_uuid} generated={datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    )
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
    from app.models import Company

    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        # admin/owner сервиса тоже может — упрощённо: владелец заказа или staff
        if not order:
            raise HTTPException(404, "Заказ не найден")
        if order.user_id != user.id and not user.staff_role:
            raise HTTPException(403, "Нет доступа")
    tax = await get_settings(db)
    buyer = await db.get(User, order.user_id)
    buyer_name = None
    buyer_inn = None
    if order.company_id:
        company = await db.get(Company, order.company_id)
        if company:
            buyer_name = company.name
            buyer_inn = company.inn
    return build_invoice_pdf(
        tax=tax,
        order=order,
        buyer_email=buyer.email if buyer else str(order.user_id),
        doc_type=doc_type,
        buyer_name=buyer_name or (order.customer_name if order.customer_name else None),
        buyer_inn=buyer_inn,
    )
