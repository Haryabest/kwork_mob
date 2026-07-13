"""Права B2B §2.5.3 — checklist разрешений и системные роли."""

from __future__ import annotations

from copy import deepcopy

PERMISSION_KEYS = (
    "can_create_orders",
    "can_cancel_own_orders",
    "can_cancel_any_orders",
    "can_view_all_company_models",
    "can_download_models",
    "can_add_publication_links",
    "can_mark_published",
    "can_invite_members",
    "can_manage_roles",
    "can_manage_api_keys",
    "can_view_finance",
)

_ALL = {k: True for k in PERMISSION_KEYS}
_NONE = {k: False for k in PERMISSION_KEYS}

SYSTEM_ROLE_PERMS: dict[str, dict[str, bool]] = {
    "owner": deepcopy(_ALL),
    "manager": {
        **_NONE,
        "can_create_orders": True,
        "can_cancel_own_orders": True,
        "can_cancel_any_orders": True,
        "can_view_all_company_models": True,
        "can_download_models": True,
        "can_add_publication_links": True,
        "can_mark_published": True,
        "can_invite_members": True,
        "can_view_finance": True,
    },
    "photographer": {
        **_NONE,
        "can_create_orders": True,
        "can_cancel_own_orders": True,
        "can_download_models": True,
        "can_add_publication_links": True,
        "can_mark_published": True,
    },
    "viewer": {
        **_NONE,
        "can_view_all_company_models": True,
        "can_download_models": True,
    },
}


def normalize_permissions(raw: dict | None) -> dict[str, bool]:
    base = deepcopy(_NONE)
    if not raw:
        return base
    for k in PERMISSION_KEYS:
        if k in raw:
            base[k] = bool(raw[k])
    return base


def merge_system(slug: str, overrides: dict | None = None) -> dict[str, bool]:
    perms = deepcopy(SYSTEM_ROLE_PERMS.get(slug, _NONE))
    if overrides:
        for k, v in overrides.items():
            if k in PERMISSION_KEYS:
                perms[k] = bool(v)
    return perms
