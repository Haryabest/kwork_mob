"""campaigns_tax_upsells_apikeys

Revision ID: 010_campaigns_tax_keys
Revises: 009_promo_tariffs_alerts
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_campaigns_tax_keys"
down_revision: Union[str, None] = "009_promo_tariffs_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("upsell_options", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("upsell_amount", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("orders", sa.Column("scale_calibration", postgresql.JSONB(), nullable=True))

    op.create_table(
        "upsell_prices",
        sa.Column("code", sa.String(length=40), primary_key=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("amount_rub", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        "INSERT INTO upsell_prices (code, title, amount_rub) VALUES "
        "('real_scale', 'Масштаб 1:1', 500), "
        "('video_360', 'Видео 360', 990), "
        "('virtual_tryon', 'Виртуальная примерка (USDZ)', 1500), "
        "('hole_filling', 'Автозаполнение пустот', 300) "
        "ON CONFLICT DO NOTHING"
    )

    op.add_column("campaigns", sa.Column("template", sa.String(length=50), nullable=True))
    op.add_column("campaigns", sa.Column("segment", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column("campaigns", sa.Column("stats", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column("campaigns", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaigns", sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaigns", sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("campaigns", sa.Column("budget_rub", sa.Integer(), nullable=True))

    op.create_table(
        "campaign_sends",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_campaign_sends_campaign_id", "campaign_sends", ["campaign_id"])

    op.create_table(
        "push_broadcasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("segment", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("stats", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "owner_tax_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="self_employed"),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("inn", sa.String(length=12), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("ogrnip", sa.String(length=15), nullable=True),
        sa.Column("ogrn", sa.String(length=13), nullable=True),
        sa.Column("kpp", sa.String(length=9), nullable=True),
        sa.Column("org_name", sa.String(length=255), nullable=True),
        sa.Column("legal_address", sa.Text(), nullable=True),
        sa.Column("bank_name", sa.String(length=255), nullable=True),
        sa.Column("bank_bik", sa.String(length=9), nullable=True),
        sa.Column("bank_account", sa.String(length=34), nullable=True),
        sa.Column("vat_rate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("INSERT INTO owner_tax_settings (id, mode) VALUES (1, 'self_employed') ON CONFLICT DO NOTHING")

    op.create_table(
        "company_api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_prefix", sa.String(length=12), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("rate_limit_per_min", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_company_api_keys_company_id", "company_api_keys", ["company_id"])
    op.create_index("ix_company_api_keys_key_prefix", "company_api_keys", ["key_prefix"])


def downgrade() -> None:
    op.drop_index("ix_company_api_keys_key_prefix", table_name="company_api_keys")
    op.drop_index("ix_company_api_keys_company_id", table_name="company_api_keys")
    op.drop_table("company_api_keys")
    op.drop_table("owner_tax_settings")
    op.drop_table("push_broadcasts")
    op.drop_index("ix_campaign_sends_campaign_id", table_name="campaign_sends")
    op.drop_table("campaign_sends")
    op.drop_column("campaigns", "budget_rub")
    op.drop_column("campaigns", "created_by_user_id")
    op.drop_column("campaigns", "stopped_at")
    op.drop_column("campaigns", "started_at")
    op.drop_column("campaigns", "stats")
    op.drop_column("campaigns", "segment")
    op.drop_column("campaigns", "template")
    op.drop_table("upsell_prices")
    op.drop_column("orders", "scale_calibration")
    op.drop_column("orders", "upsell_amount")
    op.drop_column("orders", "upsell_options")
