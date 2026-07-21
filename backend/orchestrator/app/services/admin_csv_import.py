"""CSV import компаний и промокодов §11.14."""

from __future__ import annotations

import csv
import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Company, CompanyInvitation, CompanyMember, Promocode, User
from app.services import pii as pii_svc
from app.services import promocodes as promo_svc


def _norm_header(h: str) -> str:
    key = (h or "").strip().lower().replace(" ", "_")
    aliases = {
        "название": "name",
        "компания": "name",
        "company_name": "name",
        "инн": "inn",
        "кпп": "kpp",
        "огрн": "ogrn",
        "email": "owner_email",
        "email_владельца": "owner_email",
        "owner": "owner_email",
        "код": "code",
        "скидка": "discount_value",
        "тип_скидки": "discount_type",
        "лимит": "max_uses",
        "тариф": "tier",
        "срок": "expires_at",
    }
    return aliases.get(key, key)


def _parse_rows(content: str) -> list[dict[str, str]]:
    text = content.strip()
    if not text:
        return []
    if text.startswith("\ufeff"):
        text = text[1:]
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "CSV без заголовка")
    rows: list[dict[str, str]] = []
    for raw in reader:
        row = {_norm_header(k): (v or "").strip() for k, v in raw.items() if k}
        if any(row.values()):
            rows.append(row)
    return rows


async def import_companies_csv(
    db: AsyncSession,
    content: str,
    *,
    admin_id: int,
) -> dict[str, Any]:
    """name, inn, kpp?, ogrn?, owner_email — компания или приглашение owner."""
    created: list[dict] = []
    invited: list[dict] = []
    errors: list[dict] = []

    for i, row in enumerate(_parse_rows(content), start=2):
        name = row.get("name") or row.get("company_name") or ""
        inn = row.get("inn") or ""
        owner_email = (row.get("owner_email") or "").lower()
        if not name or not inn or not owner_email:
            errors.append({"row": i, "error": "name, inn, owner_email обязательны"})
            continue
        dup = await db.scalar(select(Company.id).where(Company.inn == inn))
        if dup:
            errors.append({"row": i, "error": f"ИНН {inn} уже существует"})
            continue
        owner = await db.scalar(select(User).where(User.email == owner_email))
        if owner:
            company = Company(
                name=name,
                inn=inn,
                owner_id=owner.id,
                status="active",
                settings=pii_svc.encrypt_company_settings(
                    {
                        "kpp": row.get("kpp") or None,
                        "ogrn": row.get("ogrn") or None,
                        "imported_by_admin": admin_id,
                    }
                ),
            )
            db.add(company)
            await db.flush()
            existing_m = await db.scalar(
                select(CompanyMember).where(
                    CompanyMember.company_id == company.id,
                    CompanyMember.user_id == owner.id,
                )
            )
            if not existing_m:
                db.add(CompanyMember(company_id=company.id, user_id=owner.id, role="owner"))
            if owner.account_type != "legal":
                owner.account_type = "legal"
                owner.status = "active_legal"
            db.add(
                AuditLog(
                    company_id=company.id,
                    user_id=admin_id,
                    action="company_csv_import",
                    details={"inn": inn, "owner_email": owner_email},
                )
            )
            created.append({"row": i, "company_id": company.id, "owner_email": owner_email})
            continue

        token = secrets.token_urlsafe(24)
        inv = CompanyInvitation(
            token=token,
            company_id=None,
            inviter_id=admin_id,
            email=owner_email,
            role="owner",
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            meta={
                "import_company": {
                    "name": name,
                    "inn": inn,
                    "kpp": row.get("kpp") or None,
                    "ogrn": row.get("ogrn") or None,
                }
            },
        )
        db.add(inv)
        await db.flush()
        invited.append(
            {
                "row": i,
                "invitation_id": inv.id,
                "owner_email": owner_email,
                "invite_token": token,
            }
        )

    await db.flush()
    return {"created": created, "invited": invited, "errors": errors}


async def import_promocodes_csv(db: AsyncSession, content: str) -> dict[str, Any]:
    """name?, code?, discount_type, discount_value, max_uses?, tier?, expires_at?"""
    created: list[dict] = []
    errors: list[dict] = []

    for i, row in enumerate(_parse_rows(content), start=2):
        dtype = (row.get("discount_type") or "percent").lower()
        if dtype not in ("percent", "fixed"):
            errors.append({"row": i, "error": "discount_type: percent|fixed"})
            continue
        try:
            dval = int(row.get("discount_value") or 0)
        except ValueError:
            errors.append({"row": i, "error": "discount_value не число"})
            continue
        if dval < 1:
            errors.append({"row": i, "error": "discount_value >= 1"})
            continue
        plain = (row.get("code") or promo_svc.generate_plain_code()).strip().upper()
        if len(plain) < 6:
            errors.append({"row": i, "error": "code минимум 6 символов"})
            continue
        max_uses = row.get("max_uses")
        max_uses_i = int(max_uses) if max_uses else None
        tier = row.get("tier") or None
        if tier and tier not in ("small", "large"):
            errors.append({"row": i, "error": "tier: small|large"})
            continue
        expires_at = None
        raw_exp = row.get("expires_at")
        if raw_exp:
            try:
                expires_at = datetime.fromisoformat(raw_exp.replace("Z", "+00:00"))
            except ValueError:
                errors.append({"row": i, "error": "expires_at ISO date"})
                continue
        row_p = Promocode(
            code_hash=promo_svc.hash_code(plain),
            code_prefix=plain[:4],
            name=row.get("name") or None,
            discount_type=dtype,
            discount_value=dval,
            max_uses=max_uses_i,
            expires_at=expires_at,
            is_active=True,
            tier=tier,
        )
        db.add(row_p)
        await db.flush()
        created.append({"row": i, "id": row_p.id, "code": plain, "code_prefix": row_p.code_prefix})

    await db.flush()
    return {"created": created, "errors": errors}
