"""Сервис согласий и seed юридических документов."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LegalDocument, UserConsent

DEFAULT_DOCS = [
    (
        "terms",
        "Пользовательское соглашение",
        "Настоящее пользовательское соглашение регулирует использование сервиса KWork Mob "
        "для создания 3D-моделей товаров маркетплейсов. Используя сервис, вы подтверждаете "
        "согласие с условиями оказания услуг.",
    ),
    (
        "privacy",
        "Политика обработки персональных данных",
        "Мы обрабатываем персональные данные (email, опционально ФИО/ИНН, платёжные реквизиты) "
        "в соответствии с 152-ФЗ исключительно для оказания услуг, фискализации чеков и поддержки.",
    ),
    (
        "offer",
        "Публичная оферта",
        "Публичная оферта на оказание услуг генерации 3D-моделей. Оплата через ЮKassa. "
        "При загрузке запрещённого контента (NSFW, оружие, наркотики) применяется порядок: "
        "если запрещённая категория отмечена пользователем — заказ не создаётся и средства не списываются; "
        "при ложном срабатывании детектора — полный возврат и ручная проверка в течение 24 часов; "
        "при подтверждённом нарушении — постоянная блокировка без возврата (кроме ложных срабатываний).",
    ),
    (
        "rights",
        "Подтверждение прав на товары",
        "Я подтверждаю, что являюсь владельцем товаров или имею право на их 3D-моделирование "
        "и не нарушаю авторские права третьих лиц.",
    ),
    (
        "nsfw_rules",
        "Правила запрещённого контента",
        "Я ознакомлен с правилами: при самостоятельной отметке запрещённой категории заказ не создаётся; "
        "при ложном NSFW — возврат и проверка 24ч; при подтверждённом нарушении — бан без возврата "
        "(кроме ложных срабатываний).",
    ),
    (
        "publish_guide_wb",
        "Как опубликовать 3D на Wildberries",
        "WB → Товары → Карточка → Медиа → 3D-модель. GLB/USDZ ≤20 МБ.",
    ),
    (
        "publish_guide_ozon",
        "Как опубликовать 3D на Ozon",
        "Ozon Seller → Контент → 3D-модель. GLB ≤15 МБ.",
    ),
]


async def ensure_default_legal_docs(db: AsyncSession) -> None:
    exists = await db.scalar(select(LegalDocument.id).limit(1))
    if exists:
        return
    for slug, title, body in DEFAULT_DOCS:
        db.add(LegalDocument(slug=slug, title=title, body=body, version=1, is_published=True))


async def record_consents(
    db: AsyncSession,
    user_id: int,
    slugs: list[str],
    ip: str | None,
    user_agent: str | None,
) -> None:
    for slug in slugs:
        doc = await db.scalar(
            select(LegalDocument)
            .where(LegalDocument.slug == slug, LegalDocument.is_published.is_(True))
            .order_by(LegalDocument.version.desc())
            .limit(1)
        )
        if not doc:
            continue
        db.add(
            UserConsent(
                user_id=user_id,
                document_slug=slug,
                document_version=doc.version,
                ip_address=ip,
                user_agent=(user_agent or "")[:512],
            )
        )
