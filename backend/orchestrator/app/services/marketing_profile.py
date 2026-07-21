"""Маркетинговые атрибуты профиля §2.6 / §2.13."""

from __future__ import annotations

from fastapi import Request

from app.models import User

GENDER_VALUES = frozenset({"male", "female", "unspecified"})


def region_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    for header in ("X-Geo-Region", "CF-IPRegion", "X-Region-Code"):
        value = (request.headers.get(header) or "").strip()
        if value:
            return value[:128]
    country = (request.headers.get("CF-IPCountry") or request.headers.get("X-Country-Code") or "").strip()
    if country and country not in ("XX", "T1"):
        return country[:128]
    return None


def apply_region_from_request(user: User, request: Request | None, *, force: bool = False) -> bool:
    region = region_from_request(request)
    if not region:
        return False
    if force or not user.region:
        user.region = region
        return True
    return False


def card_issuer_from_payment(payment: dict) -> str | None:
    pm = payment.get("payment_method") or {}
    card = pm.get("card") or {}
    issuer = card.get("issuer_name") or card.get("bank_name")
    if issuer:
        return str(issuer).strip()[:255]
    return None


def apply_card_issuer(user: User, payment: dict) -> bool:
    issuer = card_issuer_from_payment(payment)
    if not issuer:
        return False
    user.card_bank_issuer = issuer
    return True


def normalize_gender(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip().lower()
    if v in GENDER_VALUES:
        return v
    return None
