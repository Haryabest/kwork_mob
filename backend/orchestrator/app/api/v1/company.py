"""Корпоративные функции: команда, приглашения, API-ключи, съёмка по ссылке."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user

router = APIRouter()


@router.post("/invite")
async def invite_member(user: dict = Depends(get_current_user)):
    """Пригласить сотрудника (email, роль, лимиты)."""
    raise HTTPException(501, "В разработке")


@router.get("/members")
async def list_members(user: dict = Depends(get_current_user)):
    """Список сотрудников компании."""
    raise HTTPException(501, "В разработке")


@router.delete("/members/{user_id}")
async def remove_member(user_id: int, user: dict = Depends(get_current_user)):
    """Удалить сотрудника."""
    raise HTTPException(501, "В разработке")


@router.patch("/members/{user_id}/role")
async def change_role(user_id: int, user: dict = Depends(get_current_user)):
    """Изменить роль/лимиты сотрудника."""
    raise HTTPException(501, "В разработке")


@router.patch("/members/{user_id}/limits")
async def change_limits(user_id: int, user: dict = Depends(get_current_user)):
    """Изменить лимиты сотрудника."""
    raise HTTPException(501, "В разработке")


@router.get("/members/{user_id}/tasks")
async def member_tasks(user_id: int, user: dict = Depends(get_current_user)):
    """Заказы сотрудника."""
    raise HTTPException(501, "В разработке")


@router.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    """Глобальные политики доступа компании."""
    raise HTTPException(501, "В разработке")


@router.patch("/settings")
async def update_settings(user: dict = Depends(get_current_user)):
    """Обновить глобальные политики."""
    raise HTTPException(501, "В разработке")


@router.get("/members/{member_id}/sessions")
async def member_sessions(member_id: int, user: dict = Depends(get_current_user)):
    """Активные сессии сотрудника."""
    raise HTTPException(501, "В разработке")


@router.post("/members/{member_id}/sessions/revoke")
async def revoke_sessions(member_id: int, user: dict = Depends(get_current_user)):
    """Завершить все сессии сотрудника."""
    raise HTTPException(501, "В разработке")


@router.get("/audit")
async def audit_log(user: dict = Depends(get_current_user)):
    """Журнал действий компании."""
    raise HTTPException(501, "В разработке")


@router.get("/audit/export")
async def audit_export(user: dict = Depends(get_current_user)):
    """Экспорт журнала в CSV."""
    raise HTTPException(501, "В разработке")


@router.post("/shoot_link")
async def create_shoot_link(user: dict = Depends(get_current_user)):
    """Создать одноразовую ссылку для внешнего фотографа."""
    raise HTTPException(501, "В разработке")


@router.post("/api_keys")
async def create_api_key(user: dict = Depends(get_current_user)):
    """Создать API-ключ с scope."""
    raise HTTPException(501, "В разработке")


@router.get("/api_keys")
async def list_api_keys(user: dict = Depends(get_current_user)):
    """Список API-ключей."""
    raise HTTPException(501, "В разработке")


@router.delete("/api_keys/{key_id}")
async def revoke_api_key(key_id: int, user: dict = Depends(get_current_user)):
    """Отозвать API-ключ."""
    raise HTTPException(501, "В разработке")


@router.post("/orders/bulk")
async def bulk_orders(user: dict = Depends(get_current_user)):
    """Массовая постановка задач (до 100, ERP API)."""
    raise HTTPException(501, "В разработке")
