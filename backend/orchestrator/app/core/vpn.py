"""VPN-доступ для Staff Panel (§11): только WireGuard / Tailscale CIDR."""

from ipaddress import ip_address, ip_network

from fastapi import HTTPException, Request, status

from app.core.config import settings


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def is_vpn_ip(ip: str) -> bool:
    if not ip:
        return False
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    # loopback только если VPN не обязателен (dev)
    if addr.is_loopback and not settings.ADMIN_VPN_REQUIRED:
        return True
    for cidr in settings.vpn_cidrs:
        try:
            if addr in ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def require_vpn(request: Request) -> str:
    """Блокирует доступ к staff-эндпоинтам вне VPN, если ADMIN_VPN_REQUIRED=true."""
    ip = client_ip(request)
    if not settings.ADMIN_VPN_REQUIRED:
        return ip
    if not is_vpn_ip(ip):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=(
                "Доступ к панели сотрудников только через VPN (WireGuard/Tailscale). "
                f"Ваш IP ({ip}) не в разрешённых сетях."
            ),
        )
    return ip
