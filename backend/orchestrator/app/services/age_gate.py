"""Проверка возраста 18+ (§10.8.3 / §13.5.7)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User
from app.schemas.orders import ProductCategory

# Категории 18+ (легальные, не запрещённые чек-листом)
ADULT_CATEGORIES = {ProductCategory.ADULT.value, "adult", "intimate_goods"}


def parse_birth_date(raw: str | None) -> date | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise HTTPException(400, "Некорректная дата рождения (ожидается YYYY-MM-DD)")


def age_years(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


async def ensure_age_gate(
    db: AsyncSession,
    user: User,
    *,
    category: str,
    birth_date: str | None,
) -> None:
    """Для adult: нужна верификация ≥18. Сохраняет date_of_birth / age_verified_at."""
    if category not in ADULT_CATEGORIES:
        return

    if user.age_verified_at and user.date_of_birth:
        if age_years(user.date_of_birth) >= 18:
            return

    dob = parse_birth_date(birth_date)
    if not dob:
        raise HTTPException(
            400,
            "Для категории 18+ укажите дату рождения (birth_date)",
        )
    years = age_years(dob)
    ok = years >= 18
    db.add(
        AuditLog(
            user_id=user.id,
            action="age_verification",
            details={"age": years, "success": ok, "category": category},
        )
    )
    if not ok:
        await db.flush()
        raise HTTPException(403, "Создание модели доступно только с 18 лет")

    user.date_of_birth = dob
    user.age_verified_at = datetime.now(timezone.utc)
    await db.flush()
