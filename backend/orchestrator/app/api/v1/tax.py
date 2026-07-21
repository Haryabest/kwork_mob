"""Налоговый модуль: настройки владельца + PDF/Excel."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user, require_admin
from app.core.vpn import require_vpn
from app.models import User
from app.services import tax as tax_svc
from app.services import pii as pii_svc

router = APIRouter()


def _vpn(request: Request) -> None:
    require_vpn(request)


admin_router = APIRouter(
    prefix="/admin/tax",
    tags=["Налоги"],
    dependencies=[Depends(_vpn), Depends(require_admin)],
)


class TaxSettingsBody(BaseModel):
    mode: str | None = None
    full_name: str | None = None
    inn: str | None = None
    phone: str | None = None
    ogrnip: str | None = None
    ogrn: str | None = None
    kpp: str | None = None
    org_name: str | None = None
    legal_address: str | None = None
    bank_name: str | None = None
    bank_bik: str | None = None
    bank_account: str | None = None
    vat_rate: int | None = Field(default=None, ge=0, le=20)


@admin_router.get("/settings")
async def get_tax_settings(db: AsyncSession = Depends(get_db)):
    row = await tax_svc.get_settings(db)
    await db.commit()
    return tax_svc.settings_public(row)


@admin_router.put("/settings")
async def put_tax_settings(
    body: TaxSettingsBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    staff: dict = Depends(require_admin),
):
    payload = body.model_dump(exclude_unset=True)
    row = await tax_svc.update_settings(db, payload)
    ip = request.client.host if request.client else None
    await pii_svc.audit_pii_change(
        db,
        user_id=int(staff["sub"]),
        action="admin.tax_settings_update",
        fields=[k for k in payload if k not in ("mode", "vat_rate")],
        ip=ip,
    )
    await db.commit()
    return tax_svc.settings_public(row)


@router.post("/invoice/{order_id}")
async def generate_invoice(
    order_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    data = await tax_svc.invoice_for_order(db, order_id, user, "invoice")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="invoice-{order_id}.pdf"'},
    )


@router.post("/act/{order_id}")
async def generate_act(
    order_id: int,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    data = await tax_svc.invoice_for_order(db, order_id, user, "act")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="act-{order_id}.pdf"'},
    )


@router.get("/transactions/export")
async def export_transactions(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.staff_role:
        raise HTTPException(403, "Только staff / владелец сервиса")
    data = await tax_svc.export_transactions_xlsx(db, date_from=date_from, date_to=date_to)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="transactions.xlsx"'},
    )


@admin_router.get("/transactions/export")
async def admin_export(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await tax_svc.export_transactions_xlsx(db, date_from=date_from, date_to=date_to)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="transactions.xlsx"'},
    )


@admin_router.post("/invoice/{order_id}")
async def admin_generate_invoice(
    order_id: int,
    staff: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """PDF счёт по order_id (staff §11.13)."""
    if not staff.staff_role:
        raise HTTPException(403, "Только staff")
    data = await tax_svc.invoice_for_order(db, order_id, staff, "invoice")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="invoice-{order_id}.pdf"'},
    )


@admin_router.post("/act/{order_id}")
async def admin_generate_act(
    order_id: int,
    staff: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """PDF акт по order_id (staff §11.13)."""
    if not staff.staff_role:
        raise HTTPException(403, "Только staff")
    data = await tax_svc.invoice_for_order(db, order_id, staff, "act")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="act-{order_id}.pdf"'},
    )


@admin_router.get("/instructions")
async def tax_payment_instructions():
    """§11.13 — инструкция по уплате налогов."""
    return {
        "title": "Уплата налогов (НПД / ИП / ООО)",
        "items": [
            "Самозанятый (НПД): оплата через приложение «Мой налог» до 28-го числа месяца, следующего за отчётным кварталом.",
            "ИП на УСН: авансовые платежи до 28-го числа после квартала; декларация до 25 апреля (год).",
            "ООО на УСН: авансы до 28-го после квартала; годовая декларация до 31 марта.",
            "НДС (если применимо): отражайте в счетах/актах по ставке из настроек модуля.",
            "Excel-выгрузка транзакций — для сверки с банком и «Мой налог» / 1С.",
        ],
    }


@admin_router.get("/quarterly/export")
async def admin_quarterly_export(
    year: int = Query(..., ge=2020, le=2100),
    quarter: int = Query(..., ge=1, le=4),
    db: AsyncSession = Depends(get_db),
):
    """§11.13 — квартальный отчёт транзакций (Excel)."""
    from datetime import date

    start_month = (quarter - 1) * 3 + 1
    date_from = datetime(year, start_month, 1, tzinfo=timezone.utc)
    if quarter == 4:
        date_to = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    else:
        end_month = start_month + 2
        last_day = 30 if end_month in (4, 6, 9, 11) else 31
        if end_month == 2:
            last_day = 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28
        date_to = datetime(year, end_month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    data = await tax_svc.export_transactions_xlsx(db, date_from=date_from, date_to=date_to)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="transactions-{year}-Q{quarter}.xlsx"'
        },
    )
