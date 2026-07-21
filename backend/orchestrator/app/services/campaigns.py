"""Кампании + авто-логика referral / nth_free / timed_discount (§11.7)."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Campaign,
    CampaignEntitlement,
    CampaignSend,
    Order,
    Promocode,
    PushBroadcast,
    ReferralLink,
    Transaction,
    User,
)
from app.services import email as email_svc
from app.services.promocodes import generate_plain_code, hash_code

logger = logging.getLogger(__name__)

TEMPLATES = {
    "promo_discount": "Скидка по промокоду",
    "free_generation": "Бесплатная генерация",
    "upsell_discount": "Скидка на апсейл",
    "referral": "Реферальная акция",
    "nth_free": "Каждая N-я бесплатно",
    "timed_discount": "Таймерная скидка",
    "custom_push": "Произвольный push/email",
}


async def resolve_segment(db: AsyncSession, segment: dict[str, Any]) -> list[User]:
    q = select(User).where(User.status.in_(("active", "active_individual", "active_legal", "pending_type")))
    if segment.get("marketing_opt_in_only", True):
        q = q.where(User.marketing_opt_in.is_(True))
    if segment.get("account_type"):
        q = q.where(User.account_type == segment["account_type"])
    if segment.get("gender"):
        q = q.where(User.gender == segment["gender"])
    if segment.get("region"):
        q = q.where(User.region == segment["region"])
    if segment.get("card_bank") or segment.get("card_bank_issuer"):
        bank = segment.get("card_bank") or segment.get("card_bank_issuer")
        q = q.where(User.card_bank_issuer.ilike(f"%{bank}%"))
    users = list((await db.scalars(q.limit(int(segment.get("limit", 5000))))).all())

    if segment.get("min_balance") is not None:
        users = [u for u in users if (u.balance or 0) >= int(segment["min_balance"])]
    if segment.get("has_orders"):
        out = []
        for u in users:
            n = await db.scalar(select(Order.id).where(Order.user_id == u.id).limit(1))
            if n:
                out.append(u)
        users = out
    return users


async def _create_promo(
    db: AsyncSession,
    *,
    name: str,
    discount_type: str,
    discount_value: int,
    max_uses: int | None,
    expires_at: datetime | None,
    user_id: int | None = None,
    meta: dict | None = None,
) -> tuple[Promocode, str]:
    plain = generate_plain_code()
    row = Promocode(
        code_hash=hash_code(plain),
        code_prefix=plain[:4],
        name=name,
        discount_type=discount_type,
        discount_value=discount_value,
        max_uses=max_uses,
        used_count=0,
        expires_at=expires_at,
        is_active=True,
        user_id=user_id,
        meta=meta or {},
    )
    db.add(row)
    await db.flush()
    return row, plain


async def create_campaign(
    db: AsyncSession,
    *,
    name: str,
    template: str,
    segment: dict,
    config: dict,
    budget_rub: int | None,
    created_by: int,
) -> Campaign:
    if template not in TEMPLATES:
        raise HTTPException(400, f"Шаблон: {', '.join(TEMPLATES)}")
    row = Campaign(
        name=name,
        campaign_type=template,
        template=template,
        status="draft",
        config=config or {},
        segment=segment or {},
        stats={"reach": 0, "sent": 0, "converted": 0, "revenue_rub": 0, "cost_rub": 0, "roi": 0},
        budget_rub=budget_rub,
        created_by_user_id=created_by,
    )
    db.add(row)
    await db.flush()
    return row


async def _activate_referral(db: AsyncSession, row: Campaign, users: list[User]) -> dict:
    """Реферал: каждому пользователю сегмента — персональный код; reward при N регистрациях."""
    cfg = row.config or {}
    reward_percent = int(cfg.get("reward_percent", 10))
    reward_fixed = int(cfg.get("reward_fixed_rub", 0))
    max_uses = int(cfg.get("max_referral_uses", 50))
    links = 0
    for u in users:
        code = secrets.token_urlsafe(8)[:12].upper()
        while await db.scalar(select(ReferralLink.id).where(ReferralLink.code == code)):
            code = secrets.token_urlsafe(8)[:12].upper()
        discount_type = "fixed" if reward_fixed > 0 else "percent"
        discount_value = reward_fixed if reward_fixed > 0 else reward_percent
        promo, plain = await _create_promo(
            db,
            name=f"Referral reward {row.name}",
            discount_type=discount_type,
            discount_value=discount_value,
            max_uses=1,
            expires_at=datetime.now(timezone.utc) + timedelta(days=int(cfg.get("reward_ttl_days", 60))),
            user_id=u.id,
            meta={"campaign_id": row.id, "kind": "referral_reward"},
        )
        db.add(
            ReferralLink(
                campaign_id=row.id,
                referrer_user_id=u.id,
                code=code,
                reward_promocode_id=promo.id,
                uses=0,
            )
        )
        db.add(
            CampaignEntitlement(
                campaign_id=row.id,
                user_id=u.id,
                kind="referral",
                promocode_id=promo.id,
                meta={"referral_code": code, "reward_plain_hint": plain[:2] + "****", "max_uses": max_uses},
            )
        )
        links += 1
        try:
            await email_svc.send_marketing_email(
                u.email,
                cfg.get("title") or row.name,
                inject_tracked_cta(
                    cfg.get("body") or f"Ваш реферальный код: {code}. За каждого друга — бонус.",
                    campaign_id=row.id,
                    user_id=u.id,
                    variant=None,
                    cta_url=cfg.get("cta_url")
                    or f"{settings_fallback_url().rstrip('/')}/register?ref={code}",
                    cta_label="Пригласить друга",
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("referral email %s: %s", u.email, exc)
    return {"referral_links": links}


async def _activate_nth_free(db: AsyncSession, row: Campaign, users: list[User]) -> dict:
    """Каждая N-я бесплатно: config.n (default 5). Учёт в on_order_completed."""
    cfg = row.config or {}
    n = max(int(cfg.get("n", 5)), 2)
    for u in users:
        db.add(
            CampaignEntitlement(
                campaign_id=row.id,
                user_id=u.id,
                kind="nth_free",
                meta={"n": n, "completed_count": 0},
            )
        )
        try:
            await email_svc.send_marketing_email(
                u.email,
                cfg.get("title") or row.name,
                inject_tracked_cta(
                    cfg.get("body") or f"Каждая {n}-я генерация — бесплатно!",
                    campaign_id=row.id,
                    user_id=u.id,
                    variant=None,
                    cta_url=cfg.get("cta_url") or settings_fallback_url(),
                    cta_label="Открыть приложение",
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("nth_free email: %s", exc)
    return {"n": n, "enrolled": len(users)}


async def _activate_timed_discount(db: AsyncSession, row: Campaign, users: list[User]) -> dict:
    """Таймерная скидка: общий или персональный промокод с expires_at."""
    cfg = row.config or {}
    percent = int(cfg.get("discount_percent", 15))
    hours = int(cfg.get("ttl_hours", 48))
    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    shared = bool(cfg.get("shared_code", True))
    issued = 0
    if shared:
        promo, plain = await _create_promo(
            db,
            name=f"Timed {row.name}",
            discount_type="percent",
            discount_value=percent,
            max_uses=int(cfg.get("max_uses", 1000)),
            expires_at=expires,
            meta={"campaign_id": row.id, "kind": "timed_discount"},
        )
        cfg = dict(cfg)
        cfg["issued_code"] = plain
        row.config = cfg
        for u in users:
            db.add(
                CampaignEntitlement(
                    campaign_id=row.id,
                    user_id=u.id,
                    kind="timed_discount",
                    promocode_id=promo.id,
                    meta={"code": plain, "expires_at": expires.isoformat()},
                )
            )
            try:
                body = cfg.get("body") or f"Скидка {percent}% по коду {plain} до {expires.isoformat()}"
                await email_svc.send_marketing_email(
                    u.email,
                    cfg.get("title") or row.name,
                    inject_tracked_cta(
                        body,
                        campaign_id=row.id,
                        user_id=u.id,
                        variant=None,
                        cta_url=cfg.get("cta_url"),
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("timed email: %s", exc)
            issued += 1
    else:
        for u in users:
            promo, plain = await _create_promo(
                db,
                name=f"Timed {row.name}",
                discount_type="percent",
                discount_value=percent,
                max_uses=1,
                expires_at=expires,
                user_id=u.id,
                meta={"campaign_id": row.id, "kind": "timed_discount"},
            )
            db.add(
                CampaignEntitlement(
                    campaign_id=row.id,
                    user_id=u.id,
                    kind="timed_discount",
                    promocode_id=promo.id,
                    meta={"code": plain, "expires_at": expires.isoformat()},
                )
            )
            try:
                body = cfg.get("body") or f"Персональная скидка {percent}%: {plain}"
                await email_svc.send_marketing_email(
                    u.email,
                    cfg.get("title") or row.name,
                    inject_tracked_cta(
                        body,
                        campaign_id=row.id,
                        user_id=u.id,
                        variant=None,
                        cta_url=cfg.get("cta_url"),
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("timed email: %s", exc)
            issued += 1
    return {"issued": issued, "expires_at": expires.isoformat(), "percent": percent}


async def start_campaign(db: AsyncSession, campaign_id: int) -> Campaign:
    row = await db.get(Campaign, campaign_id)
    if not row:
        raise HTTPException(404, "Кампания не найдена")
    if row.status not in ("draft", "stopped"):
        raise HTTPException(400, f"Нельзя запустить из статуса {row.status}")

    users = await resolve_segment(db, row.segment or {})
    title = (row.config or {}).get("title") or row.name
    body = (row.config or {}).get("body") or TEMPLATES.get(row.template or "", row.name)
    channel = (row.config or {}).get("channel") or "email"
    template = row.template or row.campaign_type

    auto_stats: dict = {}
    if template == "referral":
        auto_stats = await _activate_referral(db, row, users)
    elif template == "nth_free":
        auto_stats = await _activate_nth_free(db, row, users)
    elif template == "timed_discount":
        auto_stats = await _activate_timed_discount(db, row, users)
    else:
        sent = 0
        ab_enabled = bool((row.config or {}).get("ab_enabled"))
        variants = (row.config or {}).get("variants") or ["A", "B"]
        if not isinstance(variants, list) or len(variants) < 2:
            variants = ["A", "B"]
        for idx, u in enumerate(users):
            ok = False
            err = None
            variant = variants[idx % len(variants)] if ab_enabled else None
            send_title = title
            send_body = body
            if ab_enabled and isinstance((row.config or {}).get("variant_copy"), dict):
                copy = (row.config or {})["variant_copy"].get(variant) or {}
                send_title = copy.get("title") or title
                send_body = copy.get("body") or body
            try:
                if channel in ("email", "both"):
                    cta = (row.config or {}).get("cta_url")
                    mail_body = inject_tracked_cta(
                        send_body,
                        campaign_id=row.id,
                        user_id=u.id,
                        variant=variant,
                        cta_url=cta,
                        cta_label=(row.config or {}).get("cta_label") or "Открыть",
                    )
                    await email_svc.send_marketing_email(u.email, send_title, mail_body)
                    ok = True
                if channel in ("push", "both"):
                    from app.services import push as push_svc

                    # deep-link в data: tracked click URL
                    tracked = click_track_url(
                        row.id,
                        target_url=(row.config or {}).get("cta_url") or settings_fallback_url(),
                        user_id=u.id,
                        variant=variant,
                    )
                    await push_svc.send_to_user(
                        db,
                        u.id,
                        send_title,
                        send_body,
                        email_fallback=False,
                        data={"click_url": tracked, "campaign_id": str(row.id)},
                    )
                    ok = True
            except Exception as exc:  # noqa: BLE001
                err = str(exc)[:300]
                logger.warning("campaign send to %s failed: %s", u.email, exc)
            meta: dict = {}
            if err:
                meta["error"] = err
            if variant:
                meta["variant"] = variant
            meta["click_url"] = click_track_url(
                row.id,
                target_url=(row.config or {}).get("cta_url") or settings_fallback_url(),
                user_id=u.id,
                variant=variant,
            )
            db.add(
                CampaignSend(
                    campaign_id=row.id,
                    user_id=u.id,
                    channel=channel,
                    status="sent" if ok else "failed",
                    meta=meta,
                )
            )
            if ok:
                sent += 1
        auto_stats = {"sent": sent, "ab_enabled": ab_enabled}

    row.status = "running"
    row.started_at = datetime.now(timezone.utc)
    stats = dict(row.stats or {})
    stats["reach"] = len(users)
    stats["sent"] = int(auto_stats.get("sent") or auto_stats.get("issued") or auto_stats.get("enrolled") or len(users))
    stats["cost_rub"] = int(row.budget_rub or 0)
    stats["auto"] = auto_stats
    stats["converted"] = stats.get("converted") or 0
    cost = max(stats["cost_rub"], 1) if stats["cost_rub"] else 1
    stats["roi"] = round((0 - stats["cost_rub"]) / cost, 4) if stats["cost_rub"] else None
    row.stats = stats
    await db.flush()
    return row


async def on_order_completed(db: AsyncSession, *, user_id: int, order_id: int) -> None:
    """Хук: nth_free — после N завершённых заказов выдать 100% промокод."""
    ents = (
        await db.scalars(
            select(CampaignEntitlement).where(
                CampaignEntitlement.user_id == user_id,
                CampaignEntitlement.kind == "nth_free",
                CampaignEntitlement.consumed_at.is_(None),
            )
        )
    ).all()
    for ent in ents:
        camp = await db.get(Campaign, ent.campaign_id)
        if not camp or camp.status != "running":
            continue
        meta = dict(ent.meta or {})
        n = int(meta.get("n") or 5)
        cnt = int(meta.get("completed_count") or 0) + 1
        meta["completed_count"] = cnt
        ent.meta = meta
        if cnt > 0 and cnt % n == 0:
            promo, plain = await _create_promo(
                db,
                name=f"Nth free #{camp.id}",
                discount_type="percent",
                discount_value=100,
                max_uses=1,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                user_id=user_id,
                meta={"campaign_id": camp.id, "kind": "nth_free", "order_id": order_id},
            )
            ent.promocode_id = promo.id
            meta["issued_code"] = plain
            ent.meta = meta
            user = await db.get(User, user_id)
            if user and user.email:
                try:
                    await email_svc.send_marketing_email(
                        user.email,
                        "Бесплатная генерация",
                        f"Каждая {n}-я — ваша! Промокод: {plain}",
                    )
                except Exception:  # noqa: BLE001
                    pass
    await db.flush()


async def apply_referral_signup(db: AsyncSession, *, new_user_id: int, referral_code: str) -> bool:
    """При регистрации по коду — +1 use, выдать reward referrer'у (уже есть promocode)."""
    link = await db.scalar(select(ReferralLink).where(ReferralLink.code == referral_code.strip().upper()))
    if not link:
        return False
    link.uses = int(link.uses or 0) + 1
    db.add(
        CampaignEntitlement(
            campaign_id=link.campaign_id,
            user_id=new_user_id,
            kind="referral_signup",
            meta={"referrer_user_id": link.referrer_user_id, "code": link.code},
        )
    )
    await db.flush()
    return True


async def campaign_stats(db: AsyncSession, campaign_id: int) -> dict:
    from app.models import CampaignClick

    row = await db.get(Campaign, campaign_id)
    if not row:
        raise HTTPException(404, "Кампания не найдена")
    sends = (
        await db.scalars(select(CampaignSend).where(CampaignSend.campaign_id == campaign_id))
    ).all()
    sent = sum(1 for s in sends if s.status == "sent")
    failed = sum(1 for s in sends if s.status == "failed")
    clicks = int(
        await db.scalar(
            select(func.count()).select_from(CampaignClick).where(CampaignClick.campaign_id == campaign_id)
        )
        or 0
    )
    by_variant: dict[str, dict] = {}
    for s in sends:
        v = (s.meta or {}).get("variant")
        if not v:
            continue
        bucket = by_variant.setdefault(v, {"sent": 0, "failed": 0, "clicks": 0})
        if s.status == "sent":
            bucket["sent"] += 1
        elif s.status == "failed":
            bucket["failed"] += 1
    click_rows = (
        await db.scalars(select(CampaignClick).where(CampaignClick.campaign_id == campaign_id))
    ).all()
    for c in click_rows:
        v = c.variant or "?"
        bucket = by_variant.setdefault(v, {"sent": 0, "failed": 0, "clicks": 0})
        bucket["clicks"] += 1

    ents = int(
        await db.scalar(
            select(func.count()).select_from(CampaignEntitlement).where(
                CampaignEntitlement.campaign_id == campaign_id
            )
        )
        or 0
    )
    stats = dict(row.stats or {})
    if row.started_at:
        txs = (
            await db.scalars(
                select(Transaction).where(
                    Transaction.tx_type == "charge",
                    Transaction.created_at >= row.started_at,
                )
            )
        ).all()
        revenue = abs(sum(t.amount for t in txs if t.amount < 0))
        stats["revenue_rub"] = revenue
        cost = int(stats.get("cost_rub") or row.budget_rub or 0)
        stats["roi"] = round((revenue - cost) / cost, 4) if cost else None
        row.stats = stats
        await db.flush()
    reach = stats.get("reach", len(sends)) or 1
    return {
        "id": row.id,
        "name": row.name,
        "status": row.status,
        "template": row.template,
        "ab_enabled": bool((row.config or {}).get("ab_enabled")),
        "reach": stats.get("reach", len(sends)),
        "sent": sent or ents,
        "failed": failed,
        "clicked": clicks,
        "ctr": round(clicks / max(sent or ents or 1, 1), 4),
        "entitlements": ents,
        "revenue_rub": stats.get("revenue_rub", 0),
        "cost_rub": stats.get("cost_rub", 0),
        "roi": stats.get("roi"),
        "auto": stats.get("auto"),
        "conversion_rate": round((sent or ents) / max(reach, 1), 4),
        "by_variant": by_variant,
        "funnel": {
            "reach": stats.get("reach", len(sends)),
            "sent": sent or ents,
            "clicked": clicks,
            "converted": int(stats.get("converted") or 0),
        },
    }


async def track_click(
    db: AsyncSession,
    *,
    campaign_id: int,
    user_id: int | None,
    variant: str | None,
    target_url: str | None,
    ip: str | None,
) -> dict:
    from app.models import CampaignClick

    row = await db.get(Campaign, campaign_id)
    if not row:
        raise HTTPException(404, "Кампания не найдена")
    db.add(
        CampaignClick(
            campaign_id=campaign_id,
            user_id=user_id,
            variant=(variant or "")[:8] or None,
            target_url=(target_url or "")[:2000] or None,
            ip_address=ip,
        )
    )
    stats = dict(row.stats or {})
    stats["clicked"] = int(stats.get("clicked") or 0) + 1
    row.stats = stats
    await db.flush()
    return {"ok": True, "redirect": target_url or settings_fallback_url()}


def settings_fallback_url() -> str:
    from app.core.config import settings

    return settings.SELLER_PUBLIC_URL.rstrip("/") + "/dashboard"


def click_track_url(
    campaign_id: int,
    *,
    target_url: str | None = None,
    user_id: int | None = None,
    variant: str | None = None,
) -> str:
    """Публичный URL трекинга клика → редирект (§11.7 A/B)."""
    from urllib.parse import urlencode

    from app.core.config import settings

    base = settings.API_BASE_URL.rstrip("/") + f"/api/v1/campaigns/{campaign_id}/click"
    params: dict[str, str] = {}
    dest = target_url or settings_fallback_url()
    params["u"] = dest
    if user_id is not None:
        params["uid"] = str(user_id)
    if variant:
        params["v"] = str(variant)[:8]
    return f"{base}?{urlencode(params)}"


def inject_tracked_cta(
    body: str,
    *,
    campaign_id: int,
    user_id: int | None,
    variant: str | None,
    cta_url: str | None,
    cta_label: str = "Открыть",
) -> str:
    """Добавить в письмо CTA через click tracker."""
    tracked = click_track_url(
        campaign_id,
        target_url=cta_url or settings_fallback_url(),
        user_id=user_id,
        variant=variant,
    )
    text = body or ""
    if tracked in text:
        return text
    return f"{text.rstrip()}\n\n{cta_label}: {tracked}\n"


async def send_push_broadcast(
    db: AsyncSession,
    *,
    title: str,
    body: str,
    segment: dict,
    created_by: int,
    send_at: datetime | None = None,
) -> PushBroadcast:
    now = datetime.now(timezone.utc)
    if send_at and send_at > now:
        row = PushBroadcast(
            title=title,
            body=body,
            segment=segment or {},
            status="scheduled",
            created_by_user_id=created_by,
            stats={"scheduled_at": send_at.isoformat()},
        )
        db.add(row)
        await db.flush()
        return row

    row = PushBroadcast(
        title=title,
        body=body,
        segment=segment or {},
        status="sending",
        created_by_user_id=created_by,
        stats={},
    )
    db.add(row)
    await db.flush()
    return await _deliver_push_broadcast(db, row)


async def _deliver_push_broadcast(db: AsyncSession, row: PushBroadcast) -> PushBroadcast:
    from app.services import push as push_svc

    users = await resolve_segment(db, row.segment or {})
    result = await push_svc.send_to_users(db, [u.id for u in users], row.title, row.body)
    row.status = "sent"
    row.sent_at = datetime.now(timezone.utc)
    prev = dict(row.stats or {})
    row.stats = {
        **prev,
        "reach": result["reach"],
        "sent": result["pushed"] + result["emailed"],
        "pushed": result["pushed"],
        "emailed": result["emailed"],
        "channel": "fcm+email_fallback",
        "fcm_configured": result["fcm_configured"],
    }
    await db.flush()
    return row


async def dispatch_scheduled_push_broadcasts(db: AsyncSession) -> dict:
    """Отправка push с status=scheduled и scheduled_at <= now."""
    now = datetime.now(timezone.utc)
    rows = (
        await db.scalars(select(PushBroadcast).where(PushBroadcast.status == "scheduled").limit(50))
    ).all()
    sent = 0
    for row in rows:
        raw = (row.stats or {}).get("scheduled_at")
        if not raw:
            continue
        try:
            due = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if due <= now:
            row.status = "sending"
            await _deliver_push_broadcast(db, row)
            sent += 1
    return {"processed": sent}
