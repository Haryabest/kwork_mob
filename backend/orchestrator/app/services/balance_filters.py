"""Server-side saved balance transaction filters §20.3.4 / §8."""

from __future__ import annotations

import uuid
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
MAX_PRESETS = 10


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


def _presets_bucket(root: dict[str, Any], *, company_id: int | None) -> list[dict[str, Any]]:
    presets = root.get("presets")
    if not isinstance(presets, dict):
        return []
    key = f"company_{company_id}" if company_id else "personal"
    raw = presets.get(key)
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        if not pid or not name:
            continue
        payload = {k: v for k, v in item.items() if k not in ("id", "name")}
        filters = _normalize_company(payload) if company_id else _normalize_personal(payload)
        out.append({"id": pid, "name": name, **filters})
    return out


def list_presets(user: User, *, company_id: int | None = None) -> list[dict[str, Any]]:
    return _presets_bucket(_root(user), company_id=company_id)


async def upsert_preset(
    db: AsyncSession,
    user: User,
    *,
    name: str,
    filters: dict[str, Any],
    company_id: int | None = None,
    preset_id: str | None = None,
) -> dict[str, Any]:
    label = name.strip()[:64]
    if not label:
        raise ValueError("empty_name")
    normalized = _normalize_company(filters) if company_id else _normalize_personal(filters)
    prefs = dict(user.notification_prefs or {})
    root = _root(user)
    presets = root.get("presets")
    if not isinstance(presets, dict):
        presets = {}
    key = f"company_{company_id}" if company_id else "personal"
    items = _presets_bucket(root, company_id=company_id)
    pid = (preset_id or "").strip() or uuid.uuid4().hex[:12]
    row = {"id": pid, "name": label, **normalized}
    replaced = False
    for i, existing in enumerate(items):
        if existing["id"] == pid:
            items[i] = row
            replaced = True
            break
    if not replaced:
        if len(items) >= MAX_PRESETS:
            raise ValueError("limit")
        items.append(row)
    presets[key] = items
    root["presets"] = presets
    prefs[PREFS_KEY] = root
    user.notification_prefs = prefs
    await db.flush()
    return row


async def delete_preset(
    db: AsyncSession,
    user: User,
    *,
    preset_id: str,
    company_id: int | None = None,
) -> bool:
    prefs = dict(user.notification_prefs or {})
    root = _root(user)
    presets = root.get("presets")
    if not isinstance(presets, dict):
        return False
    key = f"company_{company_id}" if company_id else "personal"
    items = _presets_bucket(root, company_id=company_id)
    new_items = [x for x in items if x["id"] != preset_id]
    if len(new_items) == len(items):
        return False
    presets[key] = new_items
    root["presets"] = presets
    prefs[PREFS_KEY] = root
    user.notification_prefs = prefs
    await db.flush()
    return True
