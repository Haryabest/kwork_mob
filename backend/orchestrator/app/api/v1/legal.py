"""Юридические документы и согласия (§2.8)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_db_user, require_admin
from app.core.vpn import client_ip
from app.models import LegalDocument, User, UserConsent

router = APIRouter(prefix="/legal", tags=["Юридические документы"])

REQUIRED_SLUGS = ("terms", "privacy", "offer", "rights", "nsfw_rules")


class AcceptConsentsRequest(BaseModel):
    slugs: list[str] = Field(min_length=1)


class PublishDocumentRequest(BaseModel):
    title: str
    body: str


@router.get("")
async def list_latest_documents(db: AsyncSession = Depends(get_db)):
    """Актуальные опубликованные версии документов."""
    items = []
    for slug in ("terms", "privacy", "offer", "rights", "nsfw_rules"):
        doc = await db.scalar(
            select(LegalDocument)
            .where(LegalDocument.slug == slug, LegalDocument.is_published.is_(True))
            .order_by(LegalDocument.version.desc())
            .limit(1)
        )
        if doc:
            items.append(
                {
                    "slug": doc.slug,
                    "title": doc.title,
                    "version": doc.version,
                    "updated_at": doc.created_at.isoformat() if doc.created_at else None,
                }
            )
    return {"items": items}


@router.get("/pending")
async def pending_consents(user: User = Depends(get_current_db_user), db: AsyncSession = Depends(get_db)):
    """Документы, версии которых пользователь ещё не принял."""
    pending = []
    for slug in REQUIRED_SLUGS:
        doc = await db.scalar(
            select(LegalDocument)
            .where(LegalDocument.slug == slug, LegalDocument.is_published.is_(True))
            .order_by(LegalDocument.version.desc())
            .limit(1)
        )
        if not doc:
            continue
        last = await db.scalar(
            select(UserConsent)
            .where(
                UserConsent.user_id == user.id,
                UserConsent.document_slug == slug,
                UserConsent.document_version == doc.version,
            )
            .limit(1)
        )
        if not last:
            pending.append({"slug": doc.slug, "title": doc.title, "version": doc.version})
    return {"pending": pending}


@router.get("/{slug}")
async def get_document(slug: str, db: AsyncSession = Depends(get_db)):
    doc = await db.scalar(
        select(LegalDocument)
        .where(LegalDocument.slug == slug, LegalDocument.is_published.is_(True))
        .order_by(LegalDocument.version.desc())
        .limit(1)
    )
    if not doc:
        raise HTTPException(404, "Документ не найден")
    return {
        "slug": doc.slug,
        "title": doc.title,
        "body": doc.body,
        "version": doc.version,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.post("/accept")
async def accept_consents(
    body: AcceptConsentsRequest,
    request: Request,
    user: User = Depends(get_current_db_user),
    db: AsyncSession = Depends(get_db),
):
    """Повторное принятие обновлённых версий при входе."""
    ip = client_ip(request)
    ua = request.headers.get("user-agent", "")[:512]
    for slug in body.slugs:
        doc = await db.scalar(
            select(LegalDocument)
            .where(LegalDocument.slug == slug, LegalDocument.is_published.is_(True))
            .order_by(LegalDocument.version.desc())
            .limit(1)
        )
        if not doc:
            raise HTTPException(400, f"Документ {slug} не найден")
        db.add(
            UserConsent(
                user_id=user.id,
                document_slug=slug,
                document_version=doc.version,
                ip_address=ip,
                user_agent=ua,
            )
        )
    await db.commit()
    return {"message": "Согласия сохранены"}


@router.post("/admin/{slug}/publish")
async def publish_document(
    slug: str,
    body: PublishDocumentRequest,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Публикация новой версии документа (staff)."""
    current = await db.scalar(
        select(LegalDocument)
        .where(LegalDocument.slug == slug)
        .order_by(LegalDocument.version.desc())
        .limit(1)
    )
    version = (current.version + 1) if current else 1
    doc = LegalDocument(slug=slug, title=body.title, body=body.body, version=version, is_published=True)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {"slug": doc.slug, "version": doc.version, "title": doc.title}
