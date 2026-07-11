"""Создание staff-пользователей для web-admin."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import async_session
from app.core.security import hash_password
from app.models import FaqItem, User
from app.services.legal import ensure_default_legal_docs

STAFF = [
    ("admin@example.com", "admin1234", "admin"),
    ("support@example.com", "support1234", "support_agent"),
]

FAQ_SEED = [
    ("Общее", "Как создать 3D-модель?", "Снимите товар с 12 ракурсов в мобильном приложении, оплатите тариф и дождитесь генерации."),
    ("Оплата", "Какие способы оплаты?", "Банковская карта и СБП через ЮKassa. Корпоративный баланс для юрлиц."),
    ("Публикация", "Как опубликовать на Wildberries?", "Скачайте .usdz и следуйте инструкции «Как опубликовать» в карточке модели."),
]


async def main() -> None:
    async with async_session() as db:
        for email, password, role in STAFF:
            user = await db.scalar(select(User).where(User.email == email))
            if user:
                user.password_hash = hash_password(password)
                user.staff_role = role
                user.email_verified = True
                user.status = "active"
            else:
                db.add(
                    User(
                        email=email,
                        password_hash=hash_password(password),
                        staff_role=role,
                        email_verified=True,
                        status="active",
                        full_name="Staff",
                    )
                )
            print(f"Staff ready: {email} / {password} ({role})")

        count = await db.scalar(select(FaqItem.id).limit(1))
        if not count:
            for cat, q, a in FAQ_SEED:
                db.add(FaqItem(category=cat, question=q, answer=a, is_published=True))
            print("FAQ seeded")

        await ensure_default_legal_docs(db)
        print("Legal docs ready")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
