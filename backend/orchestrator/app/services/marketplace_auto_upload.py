"""§7.6 Автопубликация на WB/Ozon после генерации."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Model3D, Order
from app.services.marketplace_upload import get_credential, upload_model_to_marketplace

logger = logging.getLogger(__name__)


def _normalize_mp(value: str | None) -> str | None:
    mp = (value or "").lower().strip()
    if mp in ("wb", "wildberries"):
        return "wb"
    if mp == "ozon":
        return "ozon"
    return None


def resolve_sku(*, order: Order, payload: dict[str, Any]) -> str:
    for key in ("marketplace_sku", "sku", "offer_id", "article"):
        raw = payload.get(key) or getattr(order, key, None)
        if raw:
            return str(raw).strip()[:64]
    return str(order.id)


def schedule_after_generation(
    *,
    order: Order,
    model_uuid: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Поставить Celery-задачу автозагрузки (после commit mark_completed)."""
    if not settings.MARKETPLACE_UPLOAD_ENABLED or not settings.MARKETPLACE_AUTO_UPLOAD_ENABLED:
        return {"scheduled": False, "reason": "disabled"}
    mp = _normalize_mp(order.target_marketplace)
    if not mp:
        return {"scheduled": False, "reason": "no_target_marketplace"}
    sku = resolve_sku(order=order, payload=payload or {})
    from app.tasks.celery_app import auto_marketplace_upload_task

    auto_marketplace_upload_task.delay(model_uuid, mp, sku, order.id)
    return {"scheduled": True, "model_uuid": model_uuid, "marketplace": mp, "sku": sku}


async def run_auto_upload(
    db: AsyncSession,
    *,
    model_uuid: str,
    marketplace: str,
    sku: str,
    order_id: int,
) -> dict[str, Any]:
    """Celery worker: загрузка + auto-verify §7.6."""
    if not settings.MARKETPLACE_UPLOAD_ENABLED:
        return {"ok": False, "reason": "upload_disabled"}
    mp = _normalize_mp(marketplace)
    if not mp:
        return {"ok": False, "reason": "bad_marketplace"}
    model = await db.scalar(select(Model3D).where(Model3D.uuid == model_uuid))
    if not model or not model.glb_url:
        return {"ok": False, "reason": "model_not_ready"}
    order = await db.get(Order, order_id)
    if order and order.status != "completed":
        return {"ok": False, "reason": "order_not_completed"}
    cred = await get_credential(db, marketplace=mp, company_id=model.company_id)
    if not cred:
        return {"ok": False, "reason": "no_credential"}
    try:
        result = await upload_model_to_marketplace(
            db,
            model=model,
            marketplace=mp,
            sku=sku,
            initiated_by_user_id=model.user_id,
        )
        await db.commit()
        return {"ok": True, **result}
    except Exception as exc:  # noqa: BLE001
        logger.warning("auto marketplace upload failed model=%s: %s", model_uuid, exc)
        await db.rollback()
        return {"ok": False, "reason": str(exc)[:300]}
