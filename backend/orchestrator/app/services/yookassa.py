"""Интеграция с ЮKassa (§8). Без ключей — mock-режим для dev."""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.core.config import settings


class YookassaService:
    API = "https://api.yookassa.ru/v3"

    def __init__(self) -> None:
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY

    @property
    def configured(self) -> bool:
        return bool(self.shop_id and self.secret_key)

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
        key = idempotence_key or str(uuid.uuid4())
        if not self.configured:
            pid = f"mock_{uuid.uuid4().hex[:16]}"
            return {
                "id": pid,
                "status": "pending",
                "confirmation_url": f"{settings.API_BASE_URL}/api/docs#mock-payment-{pid}",
                "amount": amount_rub,
                "mock": True,
                "metadata": metadata or {},
            }

        payload = {
            "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description[:128],
            "metadata": metadata or {},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.API}/payments",
                json=payload,
                auth=(self.shop_id, self.secret_key),
                headers={"Idempotence-Key": key},
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "id": data["id"],
            "status": data.get("status", "pending"),
            "confirmation_url": (data.get("confirmation") or {}).get("confirmation_url"),
            "amount": amount_rub,
            "mock": False,
            "metadata": data.get("metadata") or metadata or {},
            "raw": data,
        }

    async def create_refund(self, payment_id: str, amount_rub: int, reason: str) -> dict[str, Any]:
        if not self.configured or payment_id.startswith("mock_"):
            return {"id": f"mock_refund_{uuid.uuid4().hex[:12]}", "status": "succeeded", "mock": True}
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
            resp.raise_for_status()
            return resp.json()

    def parse_webhook(self, body: dict[str, Any]) -> dict[str, Any]:
        """Извлечь полезные поля из уведомления ЮKassa."""
        obj = body.get("object") or {}
        return {
            "event": body.get("event"),
            "payment_id": obj.get("id"),
            "status": obj.get("status"),
            "amount": int(float((obj.get("amount") or {}).get("value", 0))),
            "metadata": obj.get("metadata") or {},
        }


yookassa_service = YookassaService()
