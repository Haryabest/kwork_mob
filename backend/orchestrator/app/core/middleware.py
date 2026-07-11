"""Middleware: rate limiting и X-Robots-Tag."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting: 100 req/min на пользователя, 1000 на IP."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # TODO: реализовать через Redis sliding window
        return await call_next(request)


class RobotsTagMiddleware(BaseHTTPMiddleware):
    """X-Robots-Tag: noindex для всех страниц."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
        return response
