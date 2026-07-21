"""DaData API: верификация ИНН юрлица / ИП (§2.2.2)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DADATA_PARTY_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"


@dataclass
class InnLookupResult:
    found: bool
    inn: str | None = None
    company_name: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    legal_address: str | None = None
    director_name: str | None = None
    party_type: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class InnVerifyResult:
    verified: bool
    mismatches: list[dict[str, str]]
    lookup: InnLookupResult | None = None


def configured() -> bool:
    return bool(settings.DADATA_API_KEY.strip())


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "")


def _headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Token {settings.DADATA_API_KEY.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    secret = (settings.DADATA_SECRET or "").strip()
    if secret:
        headers["X-Secret"] = secret
    return headers


def _parse_party(data: dict[str, Any]) -> InnLookupResult:
    suggestions = data.get("suggestions") or []
    if not suggestions:
        return InnLookupResult(found=False)
    item = suggestions[0]
    party = item.get("data") or {}
    name = party.get("name") or {}
    address = party.get("address") or {}
    management = party.get("management") or {}
    return InnLookupResult(
        found=True,
        inn=party.get("inn"),
        company_name=name.get("full_with_opf") or name.get("short_with_opf") or item.get("value"),
        kpp=party.get("kpp"),
        ogrn=party.get("ogrn"),
        legal_address=address.get("value") or address.get("unrestricted_value"),
        director_name=management.get("name"),
        party_type=party.get("type"),
        raw=party,
    )


async def lookup_inn(inn: str) -> InnLookupResult:
    inn = inn.strip()
    if not inn.isdigit() or len(inn) not in (10, 12):
        return InnLookupResult(found=False)

    if not configured():
        if settings.is_development:
            return InnLookupResult(
                found=True,
                inn=inn,
                company_name=f"Dev Org {inn}",
                kpp="770101001" if len(inn) == 10 else None,
                ogrn="1027700132195" if len(inn) == 10 else "315774600123456",
                legal_address="г. Москва, ул. Примерная, д. 1",
                director_name="Иванов Иван Иванович",
                party_type="LEGAL" if len(inn) == 10 else "INDIVIDUAL",
            )
        return InnLookupResult(found=False)

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                DADATA_PARTY_URL,
                headers=_headers(),
                json={"query": inn},
            )
            resp.raise_for_status()
            return _parse_party(resp.json())
    except Exception as exc:  # noqa: BLE001
        logger.warning("DaData lookup failed for inn=%s: %s", inn, exc)
        return InnLookupResult(found=False)


def _mismatch(field: str, expected: str | None, actual: str | None) -> dict[str, str] | None:
    if not actual:
        return None
    if _normalize(expected) != _normalize(actual):
        return {"field": field, "expected": expected or "", "actual": actual}
    return None


async def verify_legal_entity(
    *,
    inn: str,
    company_name: str | None,
    kpp: str | None,
    ogrn: str | None,
    legal_address: str | None,
    director_name: str | None = None,
) -> InnVerifyResult:
    lookup = await lookup_inn(inn)
    if not lookup.found:
        return InnVerifyResult(verified=False, mismatches=[{"field": "inn", "message": "ИНН не найден в реестре"}])

    mismatches: list[dict[str, str]] = []
    for item in (
        _mismatch("company_name", lookup.company_name, company_name),
        _mismatch("kpp", lookup.kpp, kpp) if len(inn) == 10 else None,
        _mismatch("ogrn", lookup.ogrn, ogrn),
        _mismatch("legal_address", lookup.legal_address, legal_address),
        _mismatch("director_name", lookup.director_name, director_name),
    ):
        if item:
            mismatches.append(item)

    return InnVerifyResult(verified=not mismatches, mismatches=mismatches, lookup=lookup)


def company_verification_allowed(settings_dict: dict | None) -> bool:
    ver = (settings_dict or {}).get("verification")
    if isinstance(ver, str):
        return ver in ("dadata_verified", "mismatch_confirmed", "dev_skipped", "manual_confirmed")
    if isinstance(ver, dict):
        return ver.get("status") in (
            "dadata_verified",
            "mismatch_confirmed",
            "dev_skipped",
            "manual_confirmed",
        )
    return False
