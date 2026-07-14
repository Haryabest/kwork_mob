"""Воронка публикации §7.9 — агрегаты PG + лог скачиваний."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Model3D,
    ModelDownloadEvent,
    ModelPublicationLink,
    Order,
    User,
)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _model_generated_clause(date_from: datetime | None, date_to: datetime | None):
    clauses = [Model3D.glb_url.isnot(None)]
    if date_from:
        clauses.append(Model3D.created_at >= _utc(date_from))
    if date_to:
        clauses.append(Model3D.created_at <= _utc(date_to))
    return and_(*clauses)


def _verified_status(model: Model3D) -> bool:
    ps = (model.publish_status or "").lower()
    return ps.startswith("verified_") or ps.startswith("api_uploaded_")


def _manual_marked(model: Model3D) -> bool:
    return (model.publish_status or "").lower().startswith("published_")


async def _load_cohort_models(
    db: AsyncSession,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    company_id: int | None = None,
    category: str | None = None,
    personal_only: bool | None = None,
) -> list[Model3D]:
    q = select(Model3D).where(_model_generated_clause(date_from, date_to))
    if company_id is not None:
        q = q.where(Model3D.company_id == company_id)
    elif personal_only is True:
        q = q.where(Model3D.company_id.is_(None))
    elif personal_only is False:
        q = q.where(Model3D.company_id.isnot(None))
    if category:
        q = q.join(Order, Order.id == Model3D.order_id).where(Order.category == category)
    return list((await db.scalars(q)).all())


async def _download_uuids(db: AsyncSession, uuids: list[str]) -> set[str]:
    if not uuids:
        return set()
    rows = (
        await db.scalars(
            select(ModelDownloadEvent.model_uuid)
            .where(ModelDownloadEvent.model_uuid.in_(uuids))
            .distinct()
        )
    ).all()
    return set(rows)


async def _link_uuids(db: AsyncSession, uuids: list[str]) -> dict[str, set[str]]:
    if not uuids:
        return {}
    rows = (
        await db.scalars(
            select(ModelPublicationLink).where(ModelPublicationLink.model_uuid.in_(uuids))
        )
    ).all()
    out: dict[str, set[str]] = {}
    for link in rows:
        out.setdefault(link.model_uuid, set()).add(link.marketplace)
    return out


async def _verified_link_uuids(db: AsyncSession, uuids: list[str]) -> dict[str, set[str]]:
    if not uuids:
        return {}
    rows = (
        await db.scalars(
            select(ModelPublicationLink).where(
                ModelPublicationLink.model_uuid.in_(uuids),
                ModelPublicationLink.status == "verified",
            )
        )
    ).all()
    out: dict[str, set[str]] = {}
    for link in rows:
        out.setdefault(link.model_uuid, set()).add(link.marketplace)
    return out


def _funnel_from_models(
    models: list[Model3D],
    *,
    downloaded: set[str],
    with_links: set[str],
    verified_links: dict[str, set[str]],
) -> dict[str, Any]:
    generated = len(models)
    dl = 0
    links = 0
    verified = 0
    manual = 0
    by_mp_verified: dict[str, int] = {"wb": 0, "ozon": 0}
    by_mp_manual: dict[str, int] = {"wb": 0, "ozon": 0, "both": 0}

    for m in models:
        uid = m.uuid
        if uid in downloaded:
            dl += 1
        if uid in with_links:
            links += 1
        is_verified = uid in verified_links or _verified_status(m)
        if is_verified:
            verified += 1
            mps = verified_links.get(uid, set())
            if not mps and m.publish_status:
                ps = m.publish_status.lower()
                if "wb" in ps or "wildberries" in ps:
                    mps = {"wb"}
                elif "ozon" in ps:
                    mps = {"ozon"}
            for mp in mps:
                key = "wb" if mp in ("wb", "wildberries") else "ozon" if mp == "ozon" else mp
                if key in by_mp_verified:
                    by_mp_verified[key] += 1
        if _manual_marked(m):
            manual += 1
            ps = (m.publish_status or "").lower()
            if "both" in ps:
                by_mp_manual["both"] += 1
            elif "wb" in ps or "wildberries" in ps:
                by_mp_manual["wb"] += 1
            elif "ozon" in ps:
                by_mp_manual["ozon"] += 1

    def pct(num: int, den: int) -> float:
        return round(num / den, 4) if den else 0.0

    return {
        "generated": generated,
        "downloaded": dl,
        "links_added": links,
        "verified": verified,
        "manual_marked": manual,
        "conversion": {
            "generated_to_downloaded": pct(dl, generated),
            "generated_to_verified": pct(verified, generated),
            "downloaded_to_verified": pct(verified, dl),
        },
        "by_marketplace": {
            "verified": by_mp_verified,
            "manual_marked": by_mp_manual,
        },
    }


async def global_funnel(
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    company_id: int | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    models = await _load_cohort_models(
        db, date_from=date_from, date_to=date_to, company_id=company_id, category=category
    )
    uuids = [m.uuid for m in models]
    downloaded = await _download_uuids(db, uuids)
    link_map = await _link_uuids(db, uuids)
    verified_map = await _verified_link_uuids(db, uuids)

    personal = [m for m in models if not m.company_id]
    company = [m for m in models if m.company_id]

    funnel = _funnel_from_models(
        models,
        downloaded=downloaded,
        with_links=set(link_map),
        verified_links=verified_map,
    )

    def _seg(sub: list[Model3D]) -> dict[str, Any]:
        su = {m.uuid for m in sub}
        return _funnel_from_models(
            sub,
            downloaded=downloaded & su,
            with_links=set(link_map) & su,
            verified_links={k: v for k, v in verified_map.items() if k in su},
        )

    by_category: dict[str, int] = {}
    if models:
        order_ids = [m.order_id for m in models if m.order_id]
        if order_ids:
            rows = (
                await db.execute(
                    select(Order.category, func.count())
                    .where(Order.id.in_(order_ids))
                    .group_by(Order.category)
                )
            ).all()
            by_category = {r[0]: int(r[1]) for r in rows}

    return {
        "period": {
            "from": date_from.isoformat() if date_from else None,
            "to": date_to.isoformat() if date_to else None,
        },
        "filters": {
            "company_id": company_id,
            "category": category,
        },
        "funnel": funnel,
        "by_segment": {
            "personal": _seg(personal) if personal else _empty_funnel(),
            "company": _seg(company) if company else _empty_funnel(),
        },
        "by_category": by_category,
    }


def _empty_funnel() -> dict[str, Any]:
    return _funnel_from_models([], downloaded=set(), with_links=set(), verified_links={})


async def team_funnel(
    db: AsyncSession,
    *,
    company_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    models = await _load_cohort_models(
        db, date_from=date_from, date_to=date_to, company_id=company_id
    )
    uuids = [m.uuid for m in models]
    downloaded = await _download_uuids(db, uuids)
    link_map = await _link_uuids(db, uuids)
    verified_map = await _verified_link_uuids(db, uuids)

    by_user: dict[int, list[Model3D]] = {}
    for m in models:
        by_user.setdefault(m.user_id, []).append(m)

    user_ids = list(by_user)
    users: dict[int, User] = {}
    if user_ids:
        for u in (await db.scalars(select(User).where(User.id.in_(user_ids)))).all():
            users[u.id] = u

    from app.services import pii as pii_svc

    items = []
    for uid, ms in sorted(by_user.items(), key=lambda x: -len(x[1])):
        mu = [m.uuid for m in ms]
        f = _funnel_from_models(
            ms,
            downloaded=downloaded & set(mu),
            with_links=set(link_map) & set(mu),
            verified_links={k: v for k, v in verified_map.items() if k in mu},
        )
        avg_days = await _avg_days_to_verify(db, ms, verified_map)
        u = users.get(uid)
        pub = pii_svc.user_public(u) if u else {}
        items.append(
            {
                "user_id": uid,
                "email": u.email if u else None,
                "full_name": pub.get("full_name"),
                "funnel": f,
                "avg_days_to_verification": avg_days,
            }
        )

    return {
        "company_id": company_id,
        "period": {
            "from": date_from.isoformat() if date_from else None,
            "to": date_to.isoformat() if date_to else None,
        },
        "totals": _funnel_from_models(
            models,
            downloaded=downloaded,
            with_links=set(link_map),
            verified_links=verified_map,
        ),
        "items": items,
    }


async def _avg_days_to_verify(
    db: AsyncSession,
    models: list[Model3D],
    verified_map: dict[str, set[str]],
) -> float | None:
    uuids = [m.uuid for m in models if m.uuid in verified_map or _verified_status(m)]
    if not uuids:
        return None
    rows = (
        await db.scalars(
            select(ModelPublicationLink).where(
                ModelPublicationLink.model_uuid.in_(uuids),
                ModelPublicationLink.verified_at.isnot(None),
            )
        )
    ).all()
    if not rows:
        return None
    created = {m.uuid: m.created_at for m in models if m.created_at}
    deltas: list[float] = []
    for link in rows:
        c = created.get(link.model_uuid)
        if c and link.verified_at:
            deltas.append((link.verified_at - c).total_seconds() / 86400)
    return round(sum(deltas) / len(deltas), 2) if deltas else None


async def log_download(
    db: AsyncSession,
    *,
    model: Model3D,
    user: User,
    request: Request | None,
    file_format: str,
    marketplace: str | None = None,
) -> None:
    ip = None
    if request is not None:
        fwd = request.headers.get("x-forwarded-for") if hasattr(request, "headers") else None
        if fwd:
            ip = fwd.split(",")[0].strip()
        elif request.client:
            ip = request.client.host
    mp = (marketplace or "").lower().strip() or None
    if mp in ("wildberries",):
        mp = "wb"
    db.add(
        ModelDownloadEvent(
            model_uuid=model.uuid,
            user_id=user.id,
            company_id=model.company_id,
            file_format=file_format,
            marketplace=mp,
            ip_address=ip,
        )
    )
    # §10.7.2 access_log
    from app.services import access_log as access_svc

    await access_svc.log_model_access(
        db,
        model=model,
        user=user,
        request=request,
        action="download",
        file_format=file_format,
    )


def funnel_to_csv(payload: dict[str, Any]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["metric", "value"])
    f = payload.get("funnel") or payload.get("totals") or {}
    for key in ("generated", "downloaded", "links_added", "verified", "manual_marked"):
        w.writerow([key, f.get(key, 0)])
    conv = f.get("conversion") or {}
    for k, v in conv.items():
        w.writerow([f"conversion.{k}", v])
    return buf.getvalue().encode("utf-8-sig")


def team_funnel_to_csv(payload: dict[str, Any]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "user_id",
            "email",
            "generated",
            "downloaded",
            "links_added",
            "verified",
            "manual_marked",
            "avg_days_to_verification",
        ]
    )
    for row in payload.get("items") or []:
        ff = row.get("funnel") or {}
        w.writerow(
            [
                row.get("user_id"),
                row.get("email"),
                ff.get("generated"),
                ff.get("downloaded"),
                ff.get("links_added"),
                ff.get("verified"),
                ff.get("manual_marked"),
                row.get("avg_days_to_verification"),
            ]
        )
    return buf.getvalue().encode("utf-8-sig")
