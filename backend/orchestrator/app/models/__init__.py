"""SQLAlchemy-модели PostgreSQL."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    inn: Mapped[str | None] = mapped_column(String(255))
    account_type: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="pending_email")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    staff_role: Mapped[str | None] = mapped_column(String(30))  # admin | support_agent
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_prefs: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    age_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    inn: Mapped[str] = mapped_column(String(12))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    balance: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    settings: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompanyMember(Base):
    __tablename__ = "company_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(50))
    role_id: Mapped[int | None] = mapped_column(ForeignKey("company_roles.id"))
    max_concurrent_orders: Mapped[int | None] = mapped_column(Integer)
    monthly_spending_limit: Mapped[int | None] = mapped_column(Integer)
    allowed_categories: Mapped[list | None] = mapped_column(ARRAY(Text))


class CompanyRole(Base):
    """Кастомные / системные роли компании (§2.5.3)."""

    __tablename__ = "company_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(50))
    permissions: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    task_uuid: Mapped[str] = mapped_column(String(36), unique=True)
    category: Mapped[str] = mapped_column(String(50))
    tier: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    amount: Mapped[int] = mapped_column(Integer)
    amount_original: Mapped[int | None] = mapped_column(Integer)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    upsell_options: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    upsell_amount: Mapped[int] = mapped_column(Integer, default=0)
    scale_calibration: Mapped[dict | None] = mapped_column(JSONB)
    promocode_id: Mapped[int | None] = mapped_column(Integer)
    yookassa_payment_id: Mapped[str | None] = mapped_column(String(64))
    zip_sha256: Mapped[str | None] = mapped_column(String(64))
    customer_name: Mapped[str | None] = mapped_column(String(255))
    receipt_email: Mapped[str | None] = mapped_column(String(255))
    device_model: Mapped[str | None] = mapped_column(String(64))
    os_version: Mapped[str | None] = mapped_column(String(64))
    model_display_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Model3D(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    glb_url: Mapped[str | None] = mapped_column(Text)
    usdz_url: Mapped[str | None] = mapped_column(Text)
    watermark_hmac: Mapped[str | None] = mapped_column(String(128))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    publish_status: Mapped[str] = mapped_column(String(30), default="not_published")
    source_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    source_extend_count: Mapped[int] = mapped_column(Integer, default=0)
    trashed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaskQueue(Base):
    __tablename__ = "task_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    payload_json: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    escalation_count: Mapped[int] = mapped_column(Integer, default=0)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Promocode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(128), unique=True)
    code_prefix: Mapped[str | None] = mapped_column(String(8))
    name: Mapped[str | None] = mapped_column(String(255))
    discount_type: Mapped[str] = mapped_column(String(20))  # percent | fixed
    discount_value: Mapped[int] = mapped_column(Integer)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tier: Mapped[str | None] = mapped_column(String(20))  # small | large | None=any
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromocodeUsage(Base):
    __tablename__ = "promocode_usages"

    id: Mapped[int] = mapped_column(primary_key=True)
    promocode_id: Mapped[int] = mapped_column(ForeignKey("promocodes.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Tariff(Base):
    __tablename__ = "tariffs"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    amount_rub: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TariffPriceHistory(Base):
    __tablename__ = "tariff_price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    tariff_code: Mapped[str] = mapped_column(ForeignKey("tariffs.code"))
    old_amount: Mapped[int] = mapped_column(Integer)
    new_amount: Mapped[int] = mapped_column(Integer)
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertSettings(Base):
    __tablename__ = "alert_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_bot_token: Mapped[str | None] = mapped_column(Text)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64))
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_to: Mapped[str | None] = mapped_column(String(255))
    thresholds: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AlertLog(Base):
    __tablename__ = "alert_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    campaign_type: Mapped[str] = mapped_column(String(50))
    template: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    config: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    segment: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    stats: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    budget_rub: Mapped[int | None] = mapped_column(Integer)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CampaignSend(Base):
    __tablename__ = "campaign_sends"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CampaignClick(Base):
    """Клики по ссылкам кампании (A/B / ROI §11.7)."""

    __tablename__ = "campaign_clicks"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    variant: Mapped[str | None] = mapped_column(String(8))
    target_url: Mapped[str | None] = mapped_column(String(2000))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PushBroadcast(Base):
    __tablename__ = "push_broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    segment: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    stats: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UpsellPrice(Base):
    __tablename__ = "upsell_prices"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    amount_rub: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OwnerTaxSettings(Base):
    __tablename__ = "owner_tax_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(20), default="self_employed")
    full_name: Mapped[str | None] = mapped_column(String(255))
    inn: Mapped[str | None] = mapped_column(String(12))
    phone: Mapped[str | None] = mapped_column(String(32))
    ogrnip: Mapped[str | None] = mapped_column(String(15))
    ogrn: Mapped[str | None] = mapped_column(String(13))
    kpp: Mapped[str | None] = mapped_column(String(9))
    org_name: Mapped[str | None] = mapped_column(String(255))
    legal_address: Mapped[str | None] = mapped_column(Text)
    bank_name: Mapped[str | None] = mapped_column(String(255))
    bank_bik: Mapped[str | None] = mapped_column(String(9))
    bank_account: Mapped[str | None] = mapped_column(String(34))
    vat_rate: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CompanyApiKey(Base):
    __tablename__ = "company_api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    key_prefix: Mapped[str] = mapped_column(String(12), index=True)
    key_hash: Mapped[str] = mapped_column(String(128))
    scopes: Mapped[list] = mapped_column(ARRAY(Text))
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, default=1000)
    daily_limit: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupportRequest(Base):
    __tablename__ = "support_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    attachments: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegalDocument(Base):
    """Юридические документы с версиями (§2.8)."""

    __tablename__ = "legal_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), index=True)  # terms | privacy | offer | rights | nsfw_rules
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserConsent(Base):
    """Фиксация согласий пользователя (§2.8.1)."""

    __tablename__ = "user_consents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_slug: Mapped[str] = mapped_column(String(50))
    document_version: Mapped[int] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NsfwBlock(Base):
    __tablename__ = "nsfw_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(50))
    refunded: Mapped[bool] = mapped_column(Boolean, default=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ServiceLogEvent(Base):
    """Централизованные логи сервисов (§11.5) — fallback при недоступности ClickHouse."""

    __tablename__ = "service_log_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    message: Mapped[str] = mapped_column(Text)
    worker_id: Mapped[str | None] = mapped_column(String(64), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    task_id: Mapped[str | None] = mapped_column(String(64), index=True)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class FaqItem(Base):
    __tablename__ = "faq_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100), default="Общее")
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    amount: Mapped[int] = mapped_column(Integer)
    tx_type: Mapped[str] = mapped_column(String(30))  # topup | charge | refund
    description: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkerNode(Base):
    """GPU-воркеры (§4): heartbeat, вес, grace period."""

    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="offline")
    gpu_name: Mapped[str | None] = mapped_column(String(128))
    gpu_load: Mapped[float | None] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(default=0.0)
    grace_period: Mapped[int] = mapped_column(Integer, default=25)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("support_requests.id"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShootLink(Base):
    """Одноразовая ссылка на загрузку 12 фото (§3 / §4)."""

    __tablename__ = "shoot_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    task_uuid: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    category: Mapped[str] = mapped_column(String(50), default="other")
    tier: Mapped[str] = mapped_column(String(20), default="small")
    status: Mapped[str] = mapped_column(String(20), default="active")
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompanyInvitation(Base):
    """Приглашение сотрудника в компанию (§2 / §20.5)."""

    __tablename__ = "company_invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(50), default="photographer")
    max_concurrent_orders: Mapped[int | None] = mapped_column(Integer)
    monthly_spending_limit: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompanyWebhook(Base):
    """B2B webhooks §4.8.7."""

    __tablename__ = "company_webhooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    secret: Mapped[str] = mapped_column(String(128), default="")
    events: Mapped[list] = mapped_column(ARRAY(Text))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompanyWebhookDelivery(Base):
    __tablename__ = "company_webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    webhook_id: Mapped[int] = mapped_column(ForeignKey("company_webhooks.id"), index=True)
    event: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=10)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|delivered|failed|dlq
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReferralLink(Base):
    """Реферальные ссылки кампании (§11.7)."""

    __tablename__ = "referral_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    referrer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    reward_promocode_id: Mapped[int | None] = mapped_column(ForeignKey("promocodes.id"))
    uses: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CampaignEntitlement(Base):
    """Начисленные бонусы кампаний (nth_free / timed / referral)."""

    __tablename__ = "campaign_entitlements"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    promocode_id: Mapped[int | None] = mapped_column(ForeignKey("promocodes.id"))
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaskConflict(Base):
    """Дубли результатов воркеров §4.8.5."""

    __tablename__ = "task_conflicts"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    worker_id: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CloudInstanceRecord(Base):
    __tablename__ = "cloud_instances"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(30))
    instance_id: Mapped[str] = mapped_column(String(128), index=True)
    worker_id: Mapped[str] = mapped_column(String(64), index=True)
    gpu: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="starting")
    image: Mapped[str | None] = mapped_column(Text)
    public_ip: Mapped[str | None] = mapped_column(String(64))
    tailscale_ip: Mapped[str | None] = mapped_column(String(64))
    rub_per_hour: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CloudOperation(Base):
    __tablename__ = "cloud_operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(30))
    instance_id: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(30))
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CloudCost(Base):
    __tablename__ = "cloud_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(30))
    instance_id: Mapped[str | None] = mapped_column(String(128))
    worker_id: Mapped[str | None] = mapped_column(String(64))
    gpu: Mapped[str | None] = mapped_column(String(64))
    hours: Mapped[float] = mapped_column(Float, default=0)
    amount_rub: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AutoscalingRule(Base):
    __tablename__ = "autoscaling_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    queue_threshold: Mapped[int] = mapped_column(Integer, default=20)
    launch_count: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str] = mapped_column(String(30), default="intelion")
    gpu: Mapped[str] = mapped_column(String(64), default="rtx4090")
    image: Mapped[str | None] = mapped_column(Text)
    idle_timeout_min: Mapped[int] = mapped_column(Integer, default=30)
    max_cloud_workers: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelPublicationLink(Base):
    __tablename__ = "model_publication_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_uuid: Mapped[str] = mapped_column(String(36), index=True)
    marketplace: Mapped[str] = mapped_column(String(20))
    url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublicationBonus(Base):
    __tablename__ = "publication_bonuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    model_uuid: Mapped[str] = mapped_column(String(36), index=True)
    bonus_type: Mapped[str] = mapped_column(String(30))
    bonus_value: Mapped[int] = mapped_column(Integer, default=0)
    promocode_id: Mapped[int | None] = mapped_column(Integer)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelShareLink(Base):
    __tablename__ = "model_share_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    short_hash: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    model_uuid: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublicationBonusSettings(Base):
    """Глобальные настройки бонуса за верификацию (§7.5.2)."""

    __tablename__ = "publication_bonus_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    bonus_type: Mapped[str] = mapped_column(String(30), default="discount_percent")
    bonus_value: Mapped[int] = mapped_column(Integer, default=10)
    promocode_ttl_days: Mapped[int] = mapped_column(Integer, default=30)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DeviceToken(Base):
    """FCM/APNs токены устройств (§3.4.3)."""

    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(Text, unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(20), default="android")
    app_version: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ModelFeedback(Base):
    """Оценка модели 1–5 + причины (§7 / §11.2.4)."""

    __tablename__ = "model_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_uuid: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    rating: Mapped[int] = mapped_column(Integer)  # 1..5
    reasons: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeletionRequest(Base):
    """Запрос на право забвения (§2.8.3), SLA 30 дней."""

    __tablename__ = "deletion_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    email_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_by: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class MarketplaceCredential(Base):
    """API-ключи WB/Ozon (§7.6 / §14.6). company_id=NULL — глобальные ключи сервиса."""

    __tablename__ = "marketplace_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    marketplace: Mapped[str] = mapped_column(String(10))  # wb | ozon
    api_key_encrypted: Mapped[str] = mapped_column(Text)
    client_id: Mapped[str | None] = mapped_column(String(64))  # Ozon Client-Id
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketplaceUploadLog(Base):
    """Лог попыток API-публикации (§14.6.4)."""

    __tablename__ = "marketplace_upload_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_uuid: Mapped[str] = mapped_column(String(36), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    marketplace: Mapped[str] = mapped_column(String(10))
    sku: Mapped[str] = mapped_column(String(64))
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|success|failed
    http_status: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    external_ref: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelDownloadEvent(Base):
    """Скачивание GLB/USDZ для воронки публикации (§7.9)."""

    __tablename__ = "model_download_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_uuid: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    file_format: Mapped[str] = mapped_column(String(10), default="glb")
    marketplace: Mapped[str | None] = mapped_column(String(20))  # wb | ozon | None
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccessLog(Base):
    """Аудит доступа к моделям §10.7.2 (presigned download)."""

    __tablename__ = "access_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    model_uuid: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(32), default="download")
    file_format: Mapped[str | None] = mapped_column(String(10))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ModerationBlacklist(Base):
    """Чёрный список слов/брендов (§10.8 / §11 модерация)."""

    __tablename__ = "moderation_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), default="general")  # general|brand|product|nsfw
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SegmentationEvent(Base):
    """Исходы серверной сегментации по устройству (§11.2.5 / §12.4.1)."""

    __tablename__ = "segmentation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    device_model: Mapped[str] = mapped_column(String(64), default="unknown", index=True)
    os_version: Mapped[str] = mapped_column(String(64), default="unknown", index=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    failed: Mapped[bool] = mapped_column(Boolean, default=False)
    avg_confidence: Mapped[float | None] = mapped_column(Float)
    method: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class SoftLaunchChecklist(Base):
    """Чек-лист soft launch — singleton id=1 (не только localStorage)."""

    __tablename__ = "soft_launch_checklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    checks: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MaintenanceChecklist(Base):
    """Чек-лист планового обслуживания §23.7 — singleton id=1."""

    __tablename__ = "maintenance_checklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    checks: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StorageNodeEvent(Base):
    """История online/offline узлов хранения §11.16.3."""

    __tablename__ = "storage_node_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[str] = mapped_column(String(64), index=True)
    node_name: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20))  # online|offline
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class DiskUsageSample(Base):
    """Сэмплы заполнения диска для прогноза §23.7."""

    __tablename__ = "disk_usage_samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    used_percent: Mapped[float | None] = mapped_column(Float)
    free_percent: Mapped[float | None] = mapped_column(Float)
    total_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
