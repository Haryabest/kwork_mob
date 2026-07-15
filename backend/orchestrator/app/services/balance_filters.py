"""Server-side saved balance transaction filters §20.3.4 / §8."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

PREFS_KEY = "balance_tx_filters"
DEFAULT_PERSONAL: dict[str, Any] = {
    "date_from": "",
    "date_to": "",
    "tx_type": "all",
    "page_size": 20,
}
DEFAULT_COMPANY: dict[str, Any] = {
    "author_id": None,
    "date_from": "",
    "date_to": "",
    "tx_type": "all",
    "page_size": 20,
}
ALLOWED_TX_TYPES = {"all", "topup", "charge", "refund"}
ALLOWED_PAGE_SIZES = {20, 50, 100}


def _root(user: User) -> dict[str, Any]:
    prefs = dict(user.notification_prefs or {})
    raw = prefs.get(PREFS_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def get_personal_filters(user: User) -> dict[str, Any]:
    root = _root(user)
    saved = root.get("personal")
    out = dict(DEFAULT_PERSONAL)
    if isinstance(saved, dict):
        out.update(_normalize_personal(saved))
    return out


def get_company_filters(user: User, company_id: int) -> dict[str, Any]:
    root = _root(user)
    companies = root.get("companies")
    out = dict(DEFAULT_COMPANY)
    if isinstance(companies, dict):
        saved = companies.get(str(company_id))
        if isinstance(saved, dict):
            out.update(_normalize_company(saved))
    return out


def _normalize_personal(raw: dict[str, Any]) -> dict[str, Any]:
    tx_type = str(raw.get("tx_type") or "all")
    page_size = int(raw.get("page_size") or 20)
    return {
        "date_from": str(raw.get("date_from") or "")[:10],
        "date_to": str(raw.get("date_to") or "")[:10],
        "tx_type": tx_type if tx_type in ALLOWED_TX_TYPES else "all",
        "page_size": page_size if page_size in ALLOWED_PAGE_SIZES else 20,
    }


def _normalize_company(raw: dict[str, Any]) -> dict[str, Any]:
    base = _normalize_personal(raw)
    author = raw.get("author_id")
    if author is None or author == "":
        base["author_id"] = None
    else:
        try:
            base["author_id"] = int(author)
        except (TypeError, ValueError):
            base["author_id"] = None
    return base


async def save_personal_filters(db: AsyncSession, user: User, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_personal(payload)
    prefs = dict(user.notification_prefs or {})
    root = _root(user)
    root["personal"] = normalized
    prefs[PREFS_KEY] = root
    user.notification_prefs = prefs
    await db.flush()
    return normalized


async def save_company_filters(
    db: AsyncSession,
    user: User,
    company_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    normalized = _normalize_company(payload)
    prefs = dict(user.notification_prefs or {})
    root = _root(user)
    companies = root.get("companies")
    if not isinstance(companies, dict):
        companies = {}
    companies[str(company_id)] = normalized
    root["companies"] = companies
    prefs[PREFS_KEY] = root
    user.notification_prefs = prefs
    await db.flush()
    return normalized
