"""§10 CSE premium — ключи из внешнего KMS компании (оркестратор не хранит ключи)."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_field
from app.models import Company, Order, TaskQueue
from app.services.company_policies import extract_policies

logger = logging.getLogger(__name__)


def cse_policy(company: Company | None) -> dict[str, Any]:
    if not company:
        return {}
    policies = extract_policies(company.settings)
    return {
        "enabled": bool(policies.get("cse_premium_kms_enabled")),
        "kms_url": (policies.get("cse_kms_url") or "").strip(),
        "has_token": bool(policies.get("cse_kms_token_encrypted")),
    }


async def fetch_worker_key_from_kms(
    db: AsyncSession,
    *,
    task_id: str,
) -> dict[str, Any]:
    """Прокси к KMS компании: воркер получает ключ только на время задачи."""
    row = await db.scalar(select(TaskQueue).where(TaskQueue.task_id == task_id))
    if not row:
        raise HTTPException(404, "Задача не найдена")
    order = await db.get(Order, row.order_id)
    if not order or not order.company_id:
        raise HTTPException(404, "CSE KMS только для корпоративных заказов")
    company = await db.get(Company, order.company_id)
    pol = cse_policy(company)
    if not pol.get("enabled"):
        raise HTTPException(409, "CSE premium KMS не включён для компании")
    kms_url = pol.get("kms_url") or ""
    if not kms_url:
        raise HTTPException(409, "cse_kms_url не настроен")
    policies = extract_policies(company.settings if company else {})
    token_enc = policies.get("cse_kms_token_encrypted") or ""
    token = decrypt_field(token_enc) if token_enc else ""
    if not token:
        raise HTTPException(409, "KMS token не настроен")

    payload = {"task_id": task_id, "order_id": order.id, "purpose": "photo_decrypt"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(kms_url.rstrip("/") + "/v1/task-key", json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("CSE KMS request failed task=%s: %s", task_id, exc)
        raise HTTPException(502, "KMS недоступен") from exc
    if resp.status_code >= 400:
        raise HTTPException(502, f"KMS error {resp.status_code}")
    body = resp.json()
    key = body.get("key") or body.get("key_b64") or body.get("data", {}).get("key")
    if not key:
        raise HTTPException(502, "KMS не вернул ключ")
    return {"task_id": task_id, "key_b64": str(key), "source": "company_kms"}
