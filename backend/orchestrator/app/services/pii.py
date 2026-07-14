"""Шифрование ПД: ФИО, адреса, реквизиты (§2.7)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_field, encrypt_field
from app.models import AuditLog, Company, OwnerTaxSettings, User

USER_PII_FIELDS = ("full_name", "phone")

TAX_PII_FIELDS = (
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
)

COMPANY_SETTINGS_PII_KEYS = (
    "kpp",
    "ogrn",
    "legal_address",
    "actual_address",
    "bank_name",
    "bik",
    "checking_account",
    "corr_account",
    "director_name",
    "docs_email",
)


def encrypt_user_fields(user: User, data: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for field in USER_PII_FIELDS:
        if field not in data:
            continue
        raw = data[field]
        if raw is None:
            setattr(user, field, None)
        else:
            setattr(user, field, encrypt_field(str(raw).strip() or None))
        changed.append(field)
    return changed


def user_public(user: User) -> dict[str, str | None]:
    return {f: decrypt_field(getattr(user, f)) for f in USER_PII_FIELDS}


def encrypt_tax_fields(row: OwnerTaxSettings, data: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for field in TAX_PII_FIELDS:
        if field not in data:
            continue
        raw = data[field]
        if raw is None:
            setattr(row, field, None)
        else:
            setattr(row, field, encrypt_field(str(raw).strip() or None))
        changed.append(field)
    return changed


def tax_row_plain(row: OwnerTaxSettings) -> dict[str, str | None]:
    return {f: decrypt_field(getattr(row, f)) for f in TAX_PII_FIELDS}


def encrypt_company_settings(settings: dict | None) -> dict:
    src = dict(settings or {})
    out: dict[str, Any] = {}
    for key, value in src.items():
        if key in COMPANY_SETTINGS_PII_KEYS and value is not None and value != "":
            out[key] = encrypt_field(str(value))
        else:
            out[key] = value
    return out


def decrypt_company_settings(settings: dict | None) -> dict:
    src = dict(settings or {})
    out: dict[str, Any] = {}
    for key, value in src.items():
        if key in COMPANY_SETTINGS_PII_KEYS and isinstance(value, str):
            out[key] = decrypt_field(value)
        else:
            out[key] = value
    return out


async def audit_pii_change(
    db: AsyncSession,
    *,
    user_id: int,
    action: str,
    fields: list[str],
    ip: str | None = None,
    company_id: int | None = None,
) -> None:
    """Лог изменений профиля / реквизитов (§2.7)."""
    db.add(
        AuditLog(
            company_id=company_id,
            user_id=user_id,
            action=action,
            details={"fields": fields, "ip": ip},
        )
    )
