"""Главный роутер API v1."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_finance,
    auth,
    campaigns,
    cloud_admin,
    company,
    faq,
    legal,
    models,
    moderation,
    orders,
    promocodes,
    shoot,
    staff_auth,
    storage,
    support,
    tax,
    user,
    watermark_admin,
    webhooks,
    worker_callback,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Аутентификация"])
api_router.include_router(staff_auth.router)  # /staff/* VPN+2FA
api_router.include_router(legal.router)
api_router.include_router(storage.router)
api_router.include_router(user.router, prefix="/user", tags=["Пользователь"])
api_router.include_router(company.router, prefix="/company", tags=["Компания"])
api_router.include_router(orders.router, prefix="/orders", tags=["Заказы"])
api_router.include_router(models.router, prefix="/models", tags=["Модели"])
api_router.include_router(promocodes.router, prefix="/promocodes", tags=["Промокоды"])
api_router.include_router(promocodes.admin_router)
api_router.include_router(support.router, prefix="/support", tags=["Поддержка"])
api_router.include_router(faq.router, prefix="/faq", tags=["FAQ"])
api_router.include_router(tax.router, prefix="/company", tags=["Налоги"])
api_router.include_router(tax.admin_router)
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(admin.router, prefix="/admin", tags=["Администрирование"])
api_router.include_router(admin_finance.router, prefix="/admin", tags=["Тарифы и алерты"])
api_router.include_router(cloud_admin.router, prefix="/admin", tags=["Облако GPU"])
api_router.include_router(campaigns.router, prefix="/admin/campaigns", tags=["Кампании"])
api_router.include_router(moderation.router, prefix="/admin/nsfw", tags=["Модерация"])
api_router.include_router(watermark_admin.router, prefix="/admin/watermark", tags=["Водяной знак"])
api_router.include_router(shoot.router)
api_router.include_router(worker_callback.router)
