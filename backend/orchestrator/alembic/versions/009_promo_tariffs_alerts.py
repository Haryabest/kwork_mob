"""promo_tariffs_alerts_refunds

Revision ID: 009_promo_tariffs_alerts
Revises: 008_escalations_age
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009_promo_tariffs_alerts"
down_revision: Union[str, None] = "008_escalations_age"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("yookassa_payment_id", sa.String(length=64), nullable=True))
    op.add_column(
        "orders",
        sa.Column("amount_original", sa.Integer(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("discount_amount", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column("promocodes", sa.Column("code_prefix", sa.String(length=8), nullable=True))
    op.add_column("promocodes", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column("promocodes", sa.Column("tier", sa.String(length=20), nullable=True))
    op.add_column("promocodes", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("promocodes", sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True))
    op.add_column(
        "promocodes",
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.add_column(
        "promocodes",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "promocode_usages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("promocode_id", sa.Integer(), sa.ForeignKey("promocodes.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("discount_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_promocode_usages_promocode_id", "promocode_usages", ["promocode_id"])

    op.create_table(
        "tariffs",
        sa.Column("code", sa.String(length=20), primary_key=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("amount_rub", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "tariff_price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tariff_code", sa.String(length=20), sa.ForeignKey("tariffs.code"), nullable=False),
        sa.Column("old_amount", sa.Integer(), nullable=False),
        sa.Column("new_amount", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        "INSERT INTO tariffs (code, title, amount_rub) VALUES "
        "('small', 'Малый', 2990), ('large', 'Крупный', 5990) "
        "ON CONFLICT DO NOTHING"
    )

    op.create_table(
        "alert_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_bot_token", sa.Text(), nullable=True),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column("telegram_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("email_to", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("INSERT INTO alert_settings (id, telegram_enabled) VALUES (1, false) ON CONFLICT DO NOTHING")

    op.create_table(
        "alert_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("alert_log")
    op.drop_table("alert_settings")
    op.drop_table("tariff_price_history")
    op.drop_table("tariffs")
    op.drop_index("ix_promocode_usages_promocode_id", table_name="promocode_usages")
    op.drop_table("promocode_usages")
    op.drop_column("promocodes", "created_at")
    op.drop_column("promocodes", "meta")
    op.drop_column("promocodes", "company_id")
    op.drop_column("promocodes", "user_id")
    op.drop_column("promocodes", "tier")
    op.drop_column("promocodes", "name")
    op.drop_column("promocodes", "code_prefix")
    op.drop_column("orders", "discount_amount")
    op.drop_column("orders", "amount_original")
    op.drop_column("orders", "yookassa_payment_id")
