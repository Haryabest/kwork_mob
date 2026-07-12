"""Интеграция с ЮKassa (§8). Production: без ключей — ошибка, без mock."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings


class YookassaService:
    API = "https://api.yookassa.ru/v3"

    def __init__(self) -> None:
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY

    @property
    def configured(self) -> bool:
        return bool(self.shop_id and self.secret_key)

    def require_configured(self) -> None:
        if not self.configured:
            raise HTTPException(
                503,
                "ЮKassa не настроена: задайте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY",
            )

    async def create_payment(
        self,
        amount_rub: int,
        description: str,
        *,
        return_url: str,
        metadata: dict[str, Any] | None = None,
        idempotence_key: str | None = None,
    ) -> dict[str, Any]:
        """Создать платёж. amount_rub — целые рубли."""
        self.require_configured()
        key = idempotence_key or str(uuid.uuid4())
        payload = {
            "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description[:128],
            "metadata": {k: str(v) for k, v in (metadata or {}).items()},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.API}/payments",
                json=payload,
                auth=(self.shop_id, self.secret_key),
                headers={"Idempotence-Key": key},
            )
            if resp.status_code >= 400:
                raise HTTPException(502, f"ЮKassa error: {resp.text[:500]}")
            data = resp.json()
        return {
            "id": data["id"],
            "status": data.get("status", "pending"),
            "confirmation_url": (data.get("confirmation") or {}).get("confirmation_url"),
            "amount": amount_rub,
            "metadata": data.get("metadata") or payload["metadata"],
            "raw": data,
        }

    async def get_payment(self, payment_id: str) -> dict[str, Any]:
        """Проверка платежа на стороне ЮKassa (webhook verification)."""
        self.require_configured()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.API}/payments/{payment_id}",
                auth=(self.shop_id, self.secret_key),
            )
            if resp.status_code >= 400:
                raise HTTPException(502, f"ЮKassa get payment error: {resp.text[:500]}")
            return resp.json()

    async def create_refund(self, payment_id: str, amount_rub: int, reason: str) -> dict[str, Any]:
        self.require_configured()
        payload = {
            "payment_id": payment_id,
            "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
            "description": reason[:250],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.API}/refunds",
                json=payload,
                auth=(self.shop_id, self.secret_key),
                headers={"Idempotence-Key": str(uuid.uuid4())},
            )
            if resp.status_code >= 400:
                raise HTTPException(502, f"ЮKassa refund error: {resp.text[:500]}")
            return resp.json()

    def parse_webhook(self, body: dict[str, Any]) -> dict[str, Any]:
        """Извлечь полезные поля из уведомления ЮKassa."""
        obj = body.get("object") or {}
        amount_raw = (obj.get("amount") or {}).get("value", 0)
        try:
            amount = int(float(amount_raw))
        except (TypeError, ValueError):
            amount = 0
        return {
            "event": body.get("event"),
            "payment_id": obj.get("id"),
            "status": obj.get("status"),
            "amount": amount,
            "metadata": obj.get("metadata") or {},
        }


yookassa_service = YookassaService()
