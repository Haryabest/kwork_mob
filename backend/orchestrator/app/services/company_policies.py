"""Глобальные политики доступа компании §2.5.4 / §20.5.6."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, User
from app.schemas.orders import ProductCategory
from app.services.company_members import audit, get_owned_company

ALL_CATEGORIES = [c.value for c in ProductCategory]

POLICY_KEYS = (
    "default_max_concurrent_orders",
    "default_monthly_spending_limit",
    "default_allowed_categories",
    "allow_photographer_download",
    "allow_photographer_add_links",
    "require_2fa_for_all",
    "auto_block_inactive_days",
    "low_balance_threshold",
)

DEFAULT_POLICIES: dict[str, Any] = {
    "default_max_concurrent_orders": 5,
    "default_monthly_spending_limit": None,
    "default_allowed_categories": list(ALL_CATEGORIES),
    "allow_photographer_download": True,
    "allow_photographer_add_links": True,
    "require_2fa_for_all": False,
    "auto_block_inactive_days": 90,
    "low_balance_threshold": 5000,
}


class CompanyPolicies(BaseModel):
    default_max_concurrent_orders: int = Field(default=5, ge=1, le=20)
    default_monthly_spending_limit: int | None = Field(default=None, ge=0)
    default_allowed_categories: list[str] = Field(default_factory=lambda: list(ALL_CATEGORIES))
    allow_photographer_download: bool = True
    allow_photographer_add_links: bool = True
    require_2fa_for_all: bool = False
    auto_block_inactive_days: int = Field(default=90, ge=1, le=3650)
    low_balance_threshold: int = Field(default=5000, ge=0)

    @field_validator("default_allowed_categories")
    @classmethod
    def _cats(cls, v: list[str]) -> list[str]:
        if not v:
            return list(ALL_CATEGORIES)
        allowed = set(ALL_CATEGORIES)
        out = [c for c in v if c in allowed]
        if not out:
            raise ValueError(f"categories из: {', '.join(ALL_CATEGORIES)}")
        return out


def normalize_policies(raw: dict | None) -> dict[str, Any]:
    base = deepcopy(DEFAULT_POLICIES)
    if not raw:
        return base
    for k in POLICY_KEYS:
        if k not in raw:
            continue
        base[k] = raw[k]
    # валидация через pydantic
    return CompanyPolicies.model_validate(base).model_dump()


def extract_policies(settings: dict | None) -> dict[str, Any]:
    """Достаёт политики из company.settings (legacy JSON + структурированные ключи)."""
    s = settings or {}
    raw = {k: s[k] for k in POLICY_KEYS if k in s}
    return normalize_policies(raw)


async def get_policies(db: AsyncSession, user: User) -> dict:
    company = await get_owned_company(db, user)
    policies = extract_policies(company.settings)
    return {
        "company_id": company.id,
        "policies": policies,
        "available_categories": list(ALL_CATEGORIES),
        "balance": company.balance,
        # совместимость со старым клиентом
        "settings": {**(company.settings or {}), **policies},
    }


async def update_policies(db: AsyncSession, user: User, body: dict) -> dict:
    company = await get_owned_company(db, user)
    current = extract_policies(company.settings)
    payload: dict[str, Any] = {}
    if isinstance(body.get("policies"), dict):
        payload.update(body["policies"])
    if isinstance(body.get("settings"), dict):
        payload.update({k: v for k, v in body["settings"].items() if k in POLICY_KEYS})
    for k in POLICY_KEYS:
        if k in body and body[k] is not None:
            payload[k] = body[k]
    merged = {**current, **payload}
    try:
        policies = normalize_policies(merged)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Некорректные политики: {exc}") from exc

    rest = {k: v for k, v in (company.settings or {}).items() if k not in POLICY_KEYS}
    company.settings = {**rest, **policies}
    await audit(
        db,
        company_id=company.id,
        user_id=user.id,
        action="company.policies",
        details=policies,
    )
    await db.flush()
    return {
        "company_id": company.id,
        "policies": policies,
        "settings": company.settings,
        "available_categories": list(ALL_CATEGORIES),
        "balance": company.balance,
    }


def policies_for_company(company: Company | None) -> dict[str, Any]:
    if not company:
        return deepcopy(DEFAULT_POLICIES)
    return extract_policies(company.settings)


def apply_policy_to_permissions(
    perms: dict[str, bool],
    *,
    role_slug: str,
    policies: dict[str, Any],
) -> dict[str, bool]:
    """Оверлей политик на права photographer (§2.5.4 / §7)."""
    out = dict(perms)
    slug = (role_slug or "").lower()
    if slug == "photographer":
        if not policies.get("allow_photographer_download", True):
            out["can_download_models"] = False
        if not policies.get("allow_photographer_add_links", True):
            out["can_add_publication_links"] = False
    return out
