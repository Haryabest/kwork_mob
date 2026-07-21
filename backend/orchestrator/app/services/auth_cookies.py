"""HttpOnly JWT cookies для web-seller (§20.10.2)."""

from __future__ import annotations

from fastapi import Request, Response

from app.core.config import settings
from app.core.security import refresh_token_expire_days

ACCESS_COOKIE = "kwork_access"
REFRESH_COOKIE = "kwork_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def web_cookie_auth(request: Request) -> bool:
    """Выдавать cookies только браузерным запросам с Origin из CORS."""
    origin = request.headers.get("origin")
    if origin and origin in settings.CORS_ORIGINS:
        return True
    referer = request.headers.get("referer") or ""
    for allowed in settings.CORS_ORIGINS:
        if referer.startswith(allowed):
            return True
    return False


def _cookie_secure() -> bool:
    return not settings.is_development


def set_auth_cookies(
    response: Response,
    *,
    access: str,
    refresh: str,
    remember_me: bool,
) -> None:
    access_max = settings.JWT_ACCESS_EXPIRE_MINUTES * 60
    refresh_days = refresh_token_expire_days(remember_me)
    refresh_max = refresh_days * 86400
    common = {
        "httponly": True,
        "secure": _cookie_secure(),
        "samesite": "lax",
    }
    response.set_cookie(ACCESS_COOKIE, access, max_age=access_max, path="/", **common)
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=refresh_max,
        path=REFRESH_COOKIE_PATH,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


def read_refresh_token(request: Request, body_token: str | None = None) -> str | None:
    return body_token or request.cookies.get(REFRESH_COOKIE)
