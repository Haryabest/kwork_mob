"""Публичные эндпоинты съёмки по ссылке + загрузка 12 фото в MinIO."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import ShootLink
from app.services import photos as photos_service

router = APIRouter(prefix="/shoot", tags=["Съёмка по ссылке"])


async def _get_active_link(db: AsyncSession, token: str) -> ShootLink:
    link = await db.scalar(select(ShootLink).where(ShootLink.token == token))
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
    if link.status != "active":
        raise HTTPException(410, "Ссылка уже использована или отозвана")
    exp = link.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        link.status = "expired"
        await db.commit()
        raise HTTPException(410, "Срок ссылки истёк")
    if link.used_count >= link.max_uses:
        raise HTTPException(410, "Лимит загрузок по ссылке исчерпан")
    return link


@router.get("/{token}")
async def get_shoot_data(token: str, db: AsyncSession = Depends(get_db)):
    """Данные съёмки + presigned PUT на 12 ракурсов."""
    link = await _get_active_link(db, token)
    prepared = photos_service.prepare_presigned_uploads(link.task_uuid)
    return {
        "token": token,
        "task_uuid": link.task_uuid,
        "category": link.category,
        "tier": link.tier,
        "expires_at": link.expires_at.isoformat(),
        "angles": prepared["angles"],
        "uploads": prepared["uploads"],
        "photos_prefix": prepared["photos_prefix"],
        "bucket": prepared["bucket"],
        "uploaded_count": photos_service.count_uploaded(link.task_uuid),
    }


@router.post("/{token}/upload")
async def upload_by_link(
    token: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Загрузка готовых 12 фото по ссылке (multipart) → MinIO photos/{task_uuid}/."""
    link = await _get_active_link(db, token)
    result = await photos_service.upload_files_to_prefix(link.task_uuid, files)
    link.used_count += 1
    if link.used_count >= link.max_uses:
        link.status = "used"
    from app.services.shoot_cleanup import _mark_uploaded

    _mark_uploaded(link)
    try:
        from app.services import company_webhooks as wh

        await wh.emit(
            db,
            company_id=link.company_id,
            event="shoot_link.uploaded",
            payload={
                "token": token,
                "task_uuid": link.task_uuid,
                "used_count": link.used_count,
                "status": link.status,
            },
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.services import company_notify as cn

        await cn.notify_company_event(
            db,
            company_id=link.company_id,
            event="photographer_uploaded",
            title="Фотограф загрузил фото",
            body=f"Ссылка {token[:8]}…: фото загружены (task {link.task_uuid[:8]}…).",
            data={"token": token, "task_uuid": link.task_uuid},
        )
    except Exception:  # noqa: BLE001
        pass
    await db.commit()
    return {**result, "status": link.status, "link_used": True}


@router.post("/{token}/complete")
async def complete_shoot(token: str, db: AsyncSession = Depends(get_db)):
    """Подтвердить, что все 12 файлов уже залиты по presigned URL."""
    link = await _get_active_link(db, token)
    photos_service.require_all_photos(link.task_uuid)
    link.used_count += 1
    if link.used_count >= link.max_uses:
        link.status = "used"
    from app.services.shoot_cleanup import _mark_uploaded

    _mark_uploaded(link)
    try:
        from app.services import company_webhooks as wh

        await wh.emit(
            db,
            company_id=link.company_id,
            event="shoot_link.uploaded",
            payload={
                "token": token,
                "task_uuid": link.task_uuid,
                "used_count": link.used_count,
                "status": link.status,
            },
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.services import company_notify as cn

        await cn.notify_company_event(
            db,
            company_id=link.company_id,
            event="photographer_uploaded",
            title="Фотограф загрузил фото",
            body=f"Ссылка {token[:8]}…: фото загружены (task {link.task_uuid[:8]}…).",
            data={"token": token, "task_uuid": link.task_uuid},
        )
    except Exception:  # noqa: BLE001
        pass
    await db.commit()
    return {
        "ok": True,
        "task_uuid": link.task_uuid,
        "photos_prefix": photos_service.photos_prefix(link.task_uuid),
        "status": link.status,
    }
