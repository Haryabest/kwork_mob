"""API-верификация публикации WB/Ozon §7.5.2 / §7.6 (дополнение к HTML parser)."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Model3D, ModelPublicationLink
from app.services.marketplace_upload import credential_api_key, get_credential

logger = logging.getLogger(__name__)

WB_NM_RE = re.compile(r"/catalog/(\d+)", re.I)
OZON_PRODUCT_RE = re.compile(r"/product/[^/]*-(\d+)", re.I)


def extract_wb_nm_id(url: str) -> int | None:
    m = WB_NM_RE.search(url)
    if m:
        return int(m.group(1))
    q = parse_qs(urlparse(url).query)
    raw = (q.get("nm") or q.get("nmId") or [None])[0]
    if raw and str(raw).isdigit():
        return int(raw)
    return None


def extract_ozon_product_id(url: str) -> str | None:
    m = OZON_PRODUCT_RE.search(url)
    if m:
        return m.group(1)
    q = parse_qs(urlparse(url).query)
    for key in ("product_id", "sku"):
        raw = (q.get(key) or [None])[0]
        if raw:
            return str(raw)
    return None


async def _wb_public_card_has_3d(nm_id: int) -> bool:
    """Публичный card API WB — признаки 3D в карточке."""
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://card.wb.ru/cards/v1/detail",
                params={"appType": 1, "curr": "rub", "dest": -1257786, "nm": nm_id},
            )
        if resp.status_code >= 400:
            return False
        data = resp.json()
        products = (data.get("data") or {}).get("products") or []
        if not products:
            return False
        product = products[0]
        raw = str(product).lower()
        if "model-viewer" in raw or ".glb" in raw or ".usdz" in raw:
            return True
        view_flags = int(product.get("viewFlags") or 0)
        # бит 3D viewer в viewFlags (эвристика WB)
        if view_flags & (1 << 13):
            return True
        for media in product.get("media") or []:
            if isinstance(media, dict):
                url = str(media.get("url") or media.get("big") or "").lower()
                if ".glb" in url or ".usdz" in url or media.get("type") == "3d":
                    return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("wb public card verify nm=%s: %s", nm_id, exc)
    return False


async def _wb_seller_media_has_3d(api_key: str, nm_id: int) -> bool:
    """Seller Content API — список медиа карточки."""
    base = settings.WB_API_BASE_URL.rstrip("/")
    url = f"{base}/content/v2/get/cards/list"
    headers = {"Authorization": api_key}
    payload: dict[str, Any] = {
        "settings": {"cursor": {"limit": 1}, "filter": {"withPhoto": -1, "textSearch": str(nm_id)}}
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            return False
        body = resp.json()
        cards = (body.get("cards") or body.get("data") or {}).get("cards") or body.get("cards") or []
        if isinstance(cards, dict):
            cards = cards.get("cards") or []
        text = str(cards).lower()
        return ".glb" in text or ".usdz" in text or "3d" in text
    except Exception as exc:  # noqa: BLE001
        logger.debug("wb seller verify nm=%s: %s", nm_id, exc)
        return False


async def _ozon_seller_has_3d(client_id: str, api_key: str, product_id: str) -> bool:
    base = settings.OZON_API_BASE_URL.rstrip("/")
    headers = {"Client-Id": client_id, "Api-Key": api_key}
    try:
        pid = int(product_id)
        payload = {"product_id": [pid]}
    except ValueError:
        payload = {"offer_id": [product_id]}
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(f"{base}/v2/product/info", headers=headers, json=payload)
        if resp.status_code >= 400:
            return False
        body = resp.json()
        items = body.get("result") or body.get("items") or []
        if isinstance(items, dict):
            items = items.get("items") or []
        text = str(items).lower()
        return "3d" in text or "model" in text or "glb" in text or "ar" in text
    except Exception as exc:  # noqa: BLE001
        logger.debug("ozon seller verify product=%s: %s", product_id, exc)
        return False


async def try_api_verify(
    db: AsyncSession,
    *,
    link: ModelPublicationLink,
    model: Model3D,
) -> tuple[bool, str]:
    """Верификация через API маркетплейса. Возвращает (ok, method)."""
    mp = (link.marketplace or "").lower()
    cred = await get_credential(db, marketplace=mp, company_id=model.company_id)
    if mp in ("wb", "wildberries"):
        nm = extract_wb_nm_id(link.url)
        if nm is None:
            return False, "parser"
        if cred:
            key = credential_api_key(cred)
            if await _wb_seller_media_has_3d(key, nm):
                return True, "wb_api"
        if await _wb_public_card_has_3d(nm):
            return True, "wb_card_api"
        return False, "wb_api"
    if mp == "ozon":
        pid = extract_ozon_product_id(link.url)
        if pid is None:
            return False, "parser"
        if cred and cred.client_id:
            key = credential_api_key(cred)
            if await _ozon_seller_has_3d(cred.client_id, key, pid):
                return True, "ozon_api"
        return False, "ozon_api"
    return False, "parser"
