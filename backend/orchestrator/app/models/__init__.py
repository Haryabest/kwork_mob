"""SQLAlchemy-модели PostgreSQL."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func, text
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
    account_type: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="pending_email")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    staff_role: Mapped[str | None] = mapped_column(String(30))  # admin | support_agent
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
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
    max_concurrent_orders: Mapped[int | None] = mapped_column(Integer)
    monthly_spending_limit: Mapped[int | None] = mapped_column(Integer)
    allowed_categories: Mapped[list | None] = mapped_column(ARRAY(Text))


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
    promocode_id: Mapped[int | None] = mapped_column(Integer)
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
    publish_status: Mapped[str] = mapped_column(String(30), default="not_published")
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Promocode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(128), unique=True)
    discount_type: Mapped[str] = mapped_column(String(20))
    discount_value: Mapped[int] = mapped_column(Integer)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    campaign_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    config: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SupportRequest(Base):
    __tablename__ = "support_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
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
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    amount: Mapped[int] = mapped_column(Integer)
    tx_type: Mapped[str] = mapped_column(String(30))  # topup | charge | refund
    description: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)
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
