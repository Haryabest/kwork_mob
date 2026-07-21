"""Cloudflare WAF / trusted proxy headers §10.7.6 / §21."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


def _skip_path(path: str) -> bool:
    return path in ("/health", "/metrics") or path.startswith("/api/v1/webhooks/")


class CloudflareWafMiddleware(BaseHTTPMiddleware):
    """Требует CF-Ray при CLOUDFLARE_WAF_ENABLED (трафик через CDN)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.CLOUDFLARE_WAF_ENABLED or _skip_path(request.url.path):
            return await call_next(request)

        cf_ray = request.headers.get("CF-Ray") or request.headers.get("cf-ray")
        if not cf_ray:
            return JSONResponse(
                {
                    "detail": "Direct access blocked — use Cloudflare WAF (§10.7.6)",
                    "code": "waf_required",
                },
                status_code=403,
            )

        cf_ip = request.headers.get("CF-Connecting-IP") or request.headers.get("cf-connecting-ip")
        if cf_ip:
            request.state.client_ip = cf_ip

        return await call_next(request)
