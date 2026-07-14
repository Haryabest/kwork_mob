"""ЮKassa: платежи, СБП QR, чеки 54-ФЗ (§8.6.4 / §8.12)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

import httpx
from fastapi import HTTPException

from app.core.config import settings

PaymentMethod = Literal["redirect", "sbp_qr"]


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
        payment_method: PaymentMethod = "redirect",
        receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Создать платёж (карта redirect или СБП QR) + опциональный чек."""
        self.require_configured()
        if amount_rub < 1:
            raise HTTPException(400, "amount_rub >= 1")
        key = idempotence_key or str(uuid.uuid4())

        if payment_method == "sbp_qr":
            confirmation: dict[str, Any] = {"type": "qr"}
        else:
            confirmation = {"type": "redirect", "return_url": return_url}

        payload: dict[str, Any] = {
            "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
            "confirmation": confirmation,
            "capture": True,
            "description": description[:128],
            "metadata": {k: str(v) for k, v in (metadata or {}).items()},
        }
        if receipt:
            payload["receipt"] = receipt

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.API}/payments",
                json=payload,
                auth=(self.shop_id, self.secret_key),
                headers={"Idempotence-Key": key},
            )
            if resp.status_code >= 400:
                from app.services import yookassa_alerts as yk_alerts

                await yk_alerts.record_error(resp.text[:300])
                raise HTTPException(502, f"ЮKassa error: {resp.text[:500]}")
            data = resp.json()

        from app.services import yookassa_alerts as yk_alerts

        await yk_alerts.record_success()
        conf = data.get("confirmation") or {}
        return {
            "id": data["id"],
            "status": data.get("status", "pending"),
            "confirmation_url": conf.get("confirmation_url"),
            "confirmation_data": conf.get("confirmation_data"),  # QR payload для СБП
            "confirmation_type": conf.get("type") or confirmation["type"],
            "amount": amount_rub,
            "payment_method": payment_method,
            "metadata": data.get("metadata") or payload["metadata"],
            "raw": data,
        }

    async def get_payment(self, payment_id: str) -> dict[str, Any]:
        self.require_configured()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.API}/payments/{payment_id}",
                auth=(self.shop_id, self.secret_key),
            )
            if resp.status_code >= 400:
                from app.services import yookassa_alerts as yk_alerts

                await yk_alerts.record_error(resp.text[:300])
                raise HTTPException(502, f"ЮKassa get payment error: {resp.text[:500]}")
            data = resp.json()
        from app.services import yookassa_alerts as yk_alerts

        await yk_alerts.record_success()
        return data

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
                from app.services import yookassa_alerts as yk_alerts

                await yk_alerts.record_error(resp.text[:300])
                raise HTTPException(502, f"ЮKassa refund error: {resp.text[:500]}")
            data = resp.json()
        from app.services import yookassa_alerts as yk_alerts

        await yk_alerts.record_success()
        return data

    async def get_refund(self, refund_id: str) -> dict[str, Any]:
        self.require_configured()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.API}/refunds/{refund_id}",
                auth=(self.shop_id, self.secret_key),
            )
            if resp.status_code >= 400:
                from app.services import yookassa_alerts as yk_alerts

                await yk_alerts.record_error(resp.text[:300])
                raise HTTPException(502, f"ЮKassa get refund error: {resp.text[:500]}")
            data = resp.json()
        from app.services import yookassa_alerts as yk_alerts

        await yk_alerts.record_success()
        return data

    def parse_webhook(self, body: dict[str, Any]) -> dict[str, Any]:
        obj = body.get("object") or {}
        amount_raw = (obj.get("amount") or {}).get("value", 0)
        try:
            amount = int(float(amount_raw))
        except (TypeError, ValueError):
            amount = 0
        event = body.get("event")
        # payment.* → object.id = payment_id; refund.* → object.id = refund_id
        payment_id = obj.get("id")
        refund_id = None
        if event and str(event).startswith("refund."):
            refund_id = obj.get("id")
            payment_id = obj.get("payment_id")
        return {
            "event": event,
            "payment_id": payment_id,
            "refund_id": refund_id,
            "status": obj.get("status"),
            "amount": amount,
            "metadata": obj.get("metadata") or {},
            "payment_method": ((obj.get("payment_method") or {}).get("type")),
            "object": obj,
        }


yookassa_service = YookassaService()
