"""Инструкции публикации на маркетплейсах §7.4 / §7.5."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, LegalDocument

DEFAULT_GUIDES: dict[str, str] = {
    "wb": (
        "Wildberries: Товары → Карточка → Медиа → 3D-модель. "
        "Загрузите GLB/USDZ ≤20 МБ. Проверьте превью на белом фоне."
    ),
    "ozon": (
        "Ozon Seller: Контент → 3D-модель товара. "
        "Загрузите GLB ≤15 МБ. Дождитесь статуса «Проверка пройдена»."
    ),
    "wildberries": (
        "Wildberries: Товары → Карточка → Медиа → 3D-модель. "
        "Загрузите GLB/USDZ ≤20 МБ."
    ),
}


def _norm_marketplace(mp: str) -> str:
    m = (mp or "ozon").strip().lower()
    return "wb" if m in ("wb", "wildberries") else "ozon"


async def get_publish_guide(
    db: AsyncSession,
    *,
    marketplace: str,
    company_id: int | None = None,
) -> dict[str, Any]:
    mp = _norm_marketplace(marketplace)
    slug = f"publish_guide_{mp}"
    doc = await db.scalar(
        select(LegalDocument)
        .where(LegalDocument.slug == slug, LegalDocument.is_published.is_(True))
        .order_by(LegalDocument.version.desc())
        .limit(1)
    )
    body = doc.body if doc else DEFAULT_GUIDES.get(mp, DEFAULT_GUIDES["ozon"])
    company_note: str | None = None
    if company_id:
        company = await db.get(Company, company_id)
        if company and isinstance(company.settings, dict):
            notes = company.settings.get("publish_instructions") or {}
            if isinstance(notes, dict):
                company_note = notes.get(mp) or notes.get("default")
            elif isinstance(notes, str):
                company_note = notes
    return {
        "marketplace": mp,
        "title": doc.title if doc else f"Как опубликовать на {mp.upper()}",
        "body": body,
        "version": doc.version if doc else 1,
        "company_note": company_note,
        "source": "cms" if doc else "default",
    }
