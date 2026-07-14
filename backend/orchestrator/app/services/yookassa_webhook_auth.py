"""Проверка подлинности webhook ЮKassa (§8.4.1): IP allowlist + API status."""

from __future__ import annotations

import ipaddress
import logging
from typing import Any

from fastapi import HTTPException, Request

from app.core.config import settings

logger = logging.getLogger(__name__)

# Официальные сети уведомлений ЮKassa
# https://yookassa.ru/developers/using-api/webhooks
DEFAULT_YOOKASSA_NETWORKS: tuple[str, ...] = (
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.154.128/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "2a02:5180::/32",
)


def _networks() -> list[ipaddress._BaseNetwork]:
    raw = (getattr(settings, "YOOKASSA_WEBHOOK_IP_ALLOWLIST", "") or "").strip()
    cidrs = [c.strip() for c in raw.split(",") if c.strip()] if raw else list(DEFAULT_YOOKASSA_NETWORKS)
    out: list[ipaddress._BaseNetwork] = []
    for c in cidrs:
        try:
            out.append(ipaddress.ip_network(c, strict=False))
        except ValueError:
            logger.warning("invalid YOOKASSA_WEBHOOK_IP_ALLOWLIST entry: %s", c)
    return out


def client_ip_from_request(request: Request) -> str | None:
    """IP клиента с учётом X-Forwarded-For (первый hop от LB)."""
    xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if xff:
        return xff
    if request.client and request.client.host:
        return request.client.host
    return None


def is_yookassa_ip(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for net in _networks():
        if addr in net:
            return True
    return False


def assert_webhook_ip(request: Request) -> str:
    """
    Hardening §8.4.1: отклонить уведомление не из сетей ЮKassa.
    Dev: YOOKASSA_WEBHOOK_IP_CHECK=false или private IPs при YOOKASSA_WEBHOOK_ALLOW_PRIVATE=true.
    """
    ip = client_ip_from_request(request) or ""
    check = bool(getattr(settings, "YOOKASSA_WEBHOOK_IP_CHECK", True))
    if not check:
        return ip or "unchecked"
    if is_yookassa_ip(ip):
        return ip
    allow_private = bool(getattr(settings, "YOOKASSA_WEBHOOK_ALLOW_PRIVATE", False))
    if allow_private and ip:
        try:
            addr = ipaddress.ip_address(ip)
            if addr.is_private or addr.is_loopback:
                return ip
        except ValueError:
            pass
    logger.warning("yookassa webhook rejected: ip=%s", ip)
    raise HTTPException(403, "YooKassa webhook: IP not allowed")


def assert_payment_authentic(
    *,
    payment: dict[str, Any],
    payment_id: str,
    expected_shop_id: str | None = None,
) -> None:
    """Доп. проверка подлинности через объект из API (id + shop)."""
    if not payment or not isinstance(payment, dict):
        raise HTTPException(400, "YooKassa: empty payment")
    if str(payment.get("id") or "") != str(payment_id):
        raise HTTPException(400, "YooKassa: payment id mismatch")
    shop = expected_shop_id or (getattr(settings, "YOOKASSA_SHOP_ID", "") or "")
    recipient = payment.get("recipient") or {}
    account_id = str(recipient.get("account_id") or payment.get("account_id") or "")
    if shop and account_id and account_id != str(shop):
        raise HTTPException(400, "YooKassa: shop_id mismatch")
