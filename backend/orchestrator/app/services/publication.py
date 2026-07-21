"""Публикация WB/Ozon: ссылки, верификация HTML, бонусы, share (§7)."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Model3D,
    ModelPublicationLink,
    ModelShareLink,
    PublicationBonus,
    PublicationBonusSettings,
    User,
)

WB_HOSTS = ("wildberries.ru", "www.wildberries.ru", "wb.ru", "www.wb.ru")
OZON_HOSTS = ("ozon.ru", "www.ozon.ru")


def detect_marketplace(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if any(host.endswith(h) for h in WB_HOSTS):
        return "wb"
    if any(host.endswith(h) for h in OZON_HOSTS):
        return "ozon"
    raise HTTPException(400, "URL должен быть с доменов wildberries.ru / ozon.ru")


async def add_publication_link(
    db: AsyncSession,
    *,
    user: User,
    model: Model3D,
    url: str,
) -> ModelPublicationLink:
    marketplace = detect_marketplace(url)
    n = await db.scalar(
        select(func.count())
        .select_from(ModelPublicationLink)
        .where(ModelPublicationLink.model_uuid == model.uuid)
    )
    if int(n or 0) >= 3:
        raise HTTPException(400, "Не более 3 ссылок на модель (§7.12)")
    row = ModelPublicationLink(
        model_uuid=model.uuid,
        marketplace=marketplace,
        url=url.strip(),
        status="pending",
        created_by_user_id=user.id,
    )
    db.add(row)
    await db.flush()
    from app.services.publication_funnel import emit_funnel_ch_event

    emit_funnel_ch_event(
        model_uuid=model.uuid,
        event_type="links_added",
        user_id=user.id,
        company_id=model.company_id,
        marketplace=marketplace,
    )
    return row


def _html_has_3d(marketplace: str, html: str) -> bool:
    low = html.lower()
    if marketplace == "wb":
        if "model-viewer" in low:
            return True
        if re.search(r'\.glb["\']|\.usdz["\']', low):
            return True
        if "3d-model" in low or "three-d" in low:
            return True
    else:
        if "3d-model" in low or "model-viewer" in low:
            return True
        if re.search(r'\.glb["\']', low):
            return True
    return False


async def verify_link(db: AsyncSession, link: ModelPublicationLink) -> ModelPublicationLink:
    link.check_attempts = int(link.check_attempts or 0) + 1
    link.last_check_at = datetime.now(timezone.utc)
    model = await db.scalar(select(Model3D).where(Model3D.uuid == link.model_uuid))
    method = "parser"
    try:
        api_ok = False
        if model:
            from app.services import publication_api_verify as api_verify

            api_ok, method = await api_verify.try_api_verify(db, link=link, model=model)
        if api_ok:
            link.status = "verified"
            link.verified_at = datetime.now(timezone.utc)
            link.error_message = None
            if model:
                model.publish_status = f"verified_{link.marketplace}"
                await award_bonus(db, model=model, user_id=link.created_by_user_id or model.user_id)
                from app.services.publication_funnel import emit_funnel_ch_event

                emit_funnel_ch_event(
                    model_uuid=model.uuid,
                    event_type="verified",
                    user_id=link.created_by_user_id or model.user_id,
                    company_id=model.company_id,
                    marketplace=link.marketplace,
                )
            await db.flush()
            link.verification_method = method  # type: ignore[attr-defined]
            return link

        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "KWorkMob-PublicationBot/1.0"},
        ) as client:
            resp = await client.get(link.url)
        html = resp.text or ""
        ok = resp.status_code < 400 and _html_has_3d(link.marketplace, html)
        if ok:
            link.status = "verified"
            link.verified_at = datetime.now(timezone.utc)
            link.error_message = None
            model = await db.scalar(select(Model3D).where(Model3D.uuid == link.model_uuid))
            if model:
                model.publish_status = f"verified_{link.marketplace}"
                await award_bonus(db, model=model, user_id=link.created_by_user_id or model.user_id)
                from app.services.publication_funnel import emit_funnel_ch_event

                emit_funnel_ch_event(
                    model_uuid=model.uuid,
                    event_type="verified",
                    user_id=link.created_by_user_id or model.user_id,
                    company_id=model.company_id,
                    marketplace=link.marketplace,
                )
        else:
            link.status = "failed"
            link.error_message = f"HTTP {resp.status_code}, 3D markers not found"
        link.verification_method = method if ok else "parser"  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        link.status = "failed"
        link.error_message = str(exc)[:300]
    await db.flush()
    return link


async def award_bonus(db: AsyncSession, *, model: Model3D, user_id: int) -> tuple[PublicationBonus | None, str | None]:
    existing = await db.scalar(
        select(PublicationBonus).where(
            PublicationBonus.model_uuid == model.uuid,
            PublicationBonus.user_id == user_id,
        )
    )
    if existing:
        return existing, None
    cfg = await db.get(PublicationBonusSettings, 1)
    if not cfg or not cfg.is_active:
        return None, None
    user = await db.get(User, user_id)
    if not user:
        return None, None
    plain = None
    promo_id = None
    if cfg.bonus_type in ("discount_percent", "fixed_amount"):
        from datetime import timedelta

        from app.models import Promocode
        from app.services.promocodes import generate_plain_code, hash_code

        plain = generate_plain_code(12)
        dtype = "percent" if cfg.bonus_type == "discount_percent" else "fixed"
        promo = Promocode(
            code_hash=hash_code(plain),
            code_prefix=plain[:4],
            name=f"Публикация {model.uuid[:8]}",
            discount_type=dtype,
            discount_value=cfg.bonus_value,
            max_uses=cfg.max_uses,
            used_count=0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=cfg.promocode_ttl_days),
            is_active=True,
            user_id=user_id,
            meta={"source": "publication_bonus", "model_uuid": model.uuid},
        )
        db.add(promo)
        await db.flush()
        promo_id = promo.id
        bonus = PublicationBonus(
            user_id=user_id,
            company_id=model.company_id,
            model_uuid=model.uuid,
            bonus_type=cfg.bonus_type,
            bonus_value=cfg.bonus_value,
            promocode_id=promo_id,
        )
        db.add(bonus)
        await db.flush()
        return bonus, plain
    if cfg.bonus_type == "free_generation":
        from app.services import tariffs as tariff_svc

        amount = await tariff_svc.get_amount(db, "small")
        user.balance = int(user.balance or 0) + amount
        bonus = PublicationBonus(
            user_id=user_id,
            company_id=model.company_id,
            model_uuid=model.uuid,
            bonus_type="free_generation",
            bonus_value=amount,
        )
        db.add(bonus)
        await db.flush()
        return bonus, None
    return None, None


async def force_verify(
    db: AsyncSession, *, link: ModelPublicationLink, model: Model3D
) -> tuple[ModelPublicationLink, str | None]:
    """Ручная верификация владельцем сервиса (§7)."""
    link.status = "verified"
    link.verified_at = datetime.now(timezone.utc)
    link.error_message = None
    model.publish_status = f"verified_{link.marketplace}"
    bonus, plain = await award_bonus(db, model=model, user_id=link.created_by_user_id or model.user_id)
    _ = bonus
    from app.services.publication_funnel import emit_funnel_ch_event

    emit_funnel_ch_event(
        model_uuid=model.uuid,
        event_type="verified",
        user_id=link.created_by_user_id or model.user_id,
        company_id=model.company_id,
        marketplace=link.marketplace,
    )
    await db.flush()
    return link, plain


async def list_links(db: AsyncSession, model_uuid: str) -> list[dict]:
    rows = (
        await db.scalars(
            select(ModelPublicationLink)
            .where(ModelPublicationLink.model_uuid == model_uuid)
            .order_by(ModelPublicationLink.id)
        )
    ).all()
    return [
        {
            "id": r.id,
            "marketplace": r.marketplace,
            "url": r.url,
            "status": r.status,
            "last_check_at": r.last_check_at.isoformat() if r.last_check_at else None,
            "verified_at": r.verified_at.isoformat() if r.verified_at else None,
            "check_attempts": r.check_attempts,
            "error_message": r.error_message,
            "verification_method": getattr(r, "verification_method", None),
        }
        for r in rows
    ]


async def verify_pending_batch(db: AsyncSession, limit: int = 50) -> dict:
    rows = (
        await db.scalars(
            select(ModelPublicationLink)
            .where(
                ModelPublicationLink.status.in_(("pending", "failed")),
                ModelPublicationLink.check_attempts < 5,
            )
            .order_by(ModelPublicationLink.id)
            .limit(limit)
        )
    ).all()
    verified = failed = 0
    for link in rows:
        await verify_link(db, link)
        if link.status == "verified":
            verified += 1
        else:
            failed += 1
    await db.commit()
    return {"checked": len(rows), "verified": verified, "failed": failed}


async def create_share_link(db: AsyncSession, *, user: User, model: Model3D, ttl_days: int = 7) -> ModelShareLink:
    h = secrets.token_urlsafe(9)[:12]
    row = ModelShareLink(
        short_hash=h,
        model_uuid=model.uuid,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=ttl_days),
    )
    db.add(row)
    await db.flush()
    return row


async def resolve_share(db: AsyncSession, short_hash: str) -> tuple[ModelShareLink, Model3D]:
    row = await db.scalar(select(ModelShareLink).where(ModelShareLink.short_hash == short_hash))
    if not row:
        raise HTTPException(404, "Ссылка не найдена")
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(410, "Ссылка истекла")
    model = await db.scalar(select(Model3D).where(Model3D.uuid == row.model_uuid))
    if not model:
        raise HTTPException(404, "Модель не найдена")
    return row, model
