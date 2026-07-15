"""Async import GLB validation queue §6.10."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Model3D, Order, User
from app.services.queue import queue_service


async def enqueue_import_validation(
    db: AsyncSession,
    *,
    model: Model3D,
    order: Order,
    glb_key: str,
    user: User,
) -> None:
    """Поставить задачу воркеру: GLB 2.0 / PBR / Draco (§6.10)."""
    order.status = "processing"
    model.publish_status = "import_validating"
    payload = {
        "pipeline": "import_validate",
        "import_glb_key": glb_key,
        "user_id": user.id,
        "order_id": order.id,
        "company_id": order.company_id,
        "category": order.category,
        "models_bucket": None,
    }
    await queue_service.enqueue(
        db,
        task_id=model.uuid,
        order_id=order.id,
        company_id=order.company_id,
        payload=payload,
        priority="high",
    )
