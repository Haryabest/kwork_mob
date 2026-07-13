"""CORS/Referer для выдачи download URL (§10.3)."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException, Request

from app.core.config import settings


def allowed_referer_hosts() -> set[str]:
    hosts: set[str] = set()
    for origin in settings.CORS_ORIGINS:
        try:
            p = urlparse(origin if "://" in origin else f"https://{origin}")
            if p.hostname:
                hosts.add(p.hostname.lower())
        except Exception:  # noqa: BLE001
            continue
    for h in settings.download_referer_hosts:
        hosts.add(h.lower())
    # публичные маркетплейсы по ТЗ
    hosts.update(
        {
            "wildberries.ru",
            "www.wildberries.ru",
            "ozon.ru",
            "www.ozon.ru",
            "seller.wildberries.ru",
            "seller.ozon.ru",
            "api.wildberries.ru",
            "api-seller.ozon.ru",
        }
    )
    return hosts


def referer_allowed(referer: str | None, *, extra_hosts: list[str] | None = None) -> bool:
    """Доп. слой: Referer должен содержать разрешённый домен (§10.3.2)."""
    if not settings.DOWNLOAD_REFERER_CHECK:
        return True
    if not referer:
        # native apps / mobile часто без Referer — пропускаем при Origin из allowlist обрабатывается отдельно
        return settings.DOWNLOAD_ALLOW_EMPTY_REFERER
    try:
        host = urlparse(referer).hostname or ""
    except Exception:  # noqa: BLE001
        return False
    host = host.lower()
    allowed = allowed_referer_hosts()
    if extra_hosts:
        allowed |= {h.lower() for h in extra_hosts}
    if host in allowed:
        return True
    return any(host.endswith("." + a) for a in allowed)


def assert_download_allowed(request: Request, *, company_domains: list[str] | None = None) -> None:
    referer = request.headers.get("referer") or request.headers.get("Referer")
    origin = request.headers.get("origin") or request.headers.get("Origin")
    if origin:
        try:
            oh = urlparse(origin).hostname
            if oh and oh.lower() in allowed_referer_hosts():
                return
            if company_domains and oh and oh.lower() in {d.lower() for d in company_domains}:
                return
        except Exception:  # noqa: BLE001
            pass
    if not referer_allowed(referer, extra_hosts=company_domains):
        raise HTTPException(
            403,
            "Скачивание запрещено: Referer/Origin не в allowlist (§10.3)",
        )
