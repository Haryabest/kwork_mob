"""OAuth providers VK ID / Yandex ID / Sber ID."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings

OAUTH_PROVIDERS = frozenset({"vk", "yandex", "sber"})


@dataclass(frozen=True)
class OAuthProviderConfig:
    key: str
    label: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str
    extra_authorize: dict[str, str]


def provider_config(provider: str) -> OAuthProviderConfig | None:
    if provider == "vk":
        cid, secret = settings.OAUTH_VK_CLIENT_ID, settings.OAUTH_VK_CLIENT_SECRET
        if not cid or not secret:
            return None
        return OAuthProviderConfig(
            key="vk",
            label="VK ID",
            client_id=cid,
            client_secret=secret,
            authorize_url="https://id.vk.ru/authorize",
            token_url="https://id.vk.ru/oauth2/auth",
            userinfo_url="https://id.vk.ru/oauth2/user_info",
            scope="email",
            extra_authorize={},
        )
    if provider == "yandex":
        cid, secret = settings.OAUTH_YANDEX_CLIENT_ID, settings.OAUTH_YANDEX_CLIENT_SECRET
        if not cid or not secret:
            return None
        return OAuthProviderConfig(
            key="yandex",
            label="Яндекс ID",
            client_id=cid,
            client_secret=secret,
            authorize_url="https://oauth.yandex.ru/authorize",
            token_url="https://oauth.yandex.ru/token",
            userinfo_url="https://login.yandex.ru/info",
            scope="login:email login:info",
            extra_authorize={},
        )
    if provider == "sber":
        cid, secret = settings.OAUTH_SBER_CLIENT_ID, settings.OAUTH_SBER_CLIENT_SECRET
        if not cid or not secret:
            return None
        return OAuthProviderConfig(
            key="sber",
            label="Сбер ID",
            client_id=cid,
            client_secret=secret,
            authorize_url="https://oauth.sber.ru/ru/prod/sberbankid/v2.1/authorize",
            token_url="https://oauth.sber.ru/ru/prod/sberbankid/v2.1/token",
            userinfo_url="https://oauth.sber.ru/ru/prod/sberbankid/v2.1/userinfo",
            scope="openid email name",
            extra_authorize={"response_type": "code"},
        )
    return None


def list_enabled_providers() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for key in ("vk", "yandex", "sber"):
        cfg = provider_config(key)
        if cfg:
            items.append({"provider": cfg.key, "label": cfg.label})
    return items


def build_authorize_url(cfg: OAuthProviderConfig, *, redirect_uri: str, state: str) -> str:
    params: dict[str, str] = {
        "client_id": cfg.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": cfg.scope,
        "state": state,
        **cfg.extra_authorize,
    }
    return f"{cfg.authorize_url}?{urlencode(params)}"


async def exchange_code(
    cfg: OAuthProviderConfig,
    *,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
    }
    headers: dict[str, str] = {}
    if cfg.key == "vk":
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(cfg.token_url, data=data, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def fetch_profile(cfg: OAuthProviderConfig, token_payload: dict[str, Any]) -> dict[str, Any]:
    access = token_payload.get("access_token")
    if not access:
        raise ValueError("no access_token")
    headers = {"Authorization": f"Bearer {access}"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        if cfg.key == "vk":
            resp = await client.post(
                cfg.userinfo_url,
                data={"access_token": access, "client_id": cfg.client_id},
            )
        elif cfg.key == "yandex":
            resp = await client.get(f"{cfg.userinfo_url}?format=json", headers=headers)
        else:
            resp = await client.get(cfg.userinfo_url, headers=headers)
        resp.raise_for_status()
        return resp.json()


def parse_profile(provider: str, raw: dict[str, Any]) -> tuple[str, str | None, str]:
    """Return provider_user_id, email, full_name."""
    if provider == "vk":
        user = raw.get("user") if isinstance(raw.get("user"), dict) else raw
        uid = str(user.get("user_id") or user.get("id") or "")
        email = user.get("email")
        name = " ".join(
            p for p in (user.get("first_name"), user.get("last_name")) if isinstance(p, str) and p
        )
        return uid, email if isinstance(email, str) else None, name
    if provider == "yandex":
        uid = str(raw.get("id") or raw.get("psuid") or "")
        email = raw.get("default_email") or raw.get("login")
        if isinstance(email, str) and "@" not in email:
            email = None
        name = raw.get("real_name") or raw.get("display_name") or ""
        return uid, email if isinstance(email, str) else None, str(name)
    uid = str(raw.get("sub") or raw.get("uid") or raw.get("id") or "")
    email = raw.get("email")
    name = raw.get("name") or raw.get("given_name") or ""
    return uid, email if isinstance(email, str) else None, str(name)
