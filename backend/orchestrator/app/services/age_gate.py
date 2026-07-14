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
    raise HTTPException(
        400,
        detail={
            "code": "invalid_birth_date",
            "message": "Некорректная дата рождения (ожидается YYYY-MM-DD)",
        },
    )


def age_years(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def is_adult_category(category: str) -> bool:
    return category in ADULT_CATEGORIES


def user_age_ok(user: User) -> bool:
    if not user.age_verified_at or not user.date_of_birth:
        return False
    return age_years(user.date_of_birth) >= 18


async def ensure_age_gate(
    db: AsyncSession,
    user: User,
    *,
    category: str,
    birth_date: str | None,
) -> dict | None:
    """Для adult: нужна верификация ≥18. Сохраняет date_of_birth / age_verified_at.

    Returns: None если категория не 18+; dict со статусом если пройдено.
    """
    if not is_adult_category(category):
        return None

    if user_age_ok(user):
        return {
            "required": True,
            "already_verified": True,
            "age_years": age_years(user.date_of_birth),  # type: ignore[arg-type]
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
        }

    dob = parse_birth_date(birth_date)
    if not dob:
        raise HTTPException(
            400,
            detail={
                "code": "age_gate_required",
                "message": "Подтвердите, что вам 18 лет. Введите дату рождения.",
                "category": category,
            },
        )
    if dob > date.today():
        raise HTTPException(
            400,
            detail={
                "code": "invalid_birth_date",
                "message": "Дата рождения не может быть в будущем",
            },
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
        raise HTTPException(
            403,
            detail={
                "code": "age_under_18",
                "message": "Создание модели доступно только с 18 лет",
                "age": years,
            },
        )

    user.date_of_birth = dob
    user.age_verified_at = datetime.now(timezone.utc)
    await db.flush()
    return {
        "required": True,
        "already_verified": False,
        "age_years": years,
        "date_of_birth": dob.isoformat(),
        "age_verified_at": user.age_verified_at.isoformat(),
    }
