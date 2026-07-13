"""Миграция: кастомные роли B2B, webhook DLQ, referral entitlements (§2.5.3 / §14.5.4 / §11.7).

Revision ID: 016_b2b_ops
Revises: 015_model_feedback
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016_b2b_ops"
down_revision: Union[str, None] = "015_model_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("permissions", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_company_roles_company_id", "company_roles", ["company_id"])
    op.create_index("uq_company_roles_company_slug", "company_roles", ["company_id", "slug"], unique=True)

    op.add_column("company_members", sa.Column("role_id", sa.Integer(), sa.ForeignKey("company_roles.id"), nullable=True))
    op.create_index("ix_company_members_role_id", "company_members", ["role_id"])

    op.add_column(
        "company_webhook_deliveries",
        sa.Column("attempt", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "company_webhook_deliveries",
        sa.Column("max_attempts", sa.Integer(), server_default="10", nullable=False),
    )
    op.add_column(
        "company_webhook_deliveries",
        sa.Column("status", sa.String(20), server_default="delivered", nullable=False),
    )
    op.add_column(
        "company_webhook_deliveries",
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_wh_deliveries_status", "company_webhook_deliveries", ["status"])
    op.create_index("ix_wh_deliveries_retry", "company_webhook_deliveries", ["next_retry_at"])

    op.create_table(
        "referral_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("referrer_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("reward_promocode_id", sa.Integer(), sa.ForeignKey("promocodes.id"), nullable=True),
        sa.Column("uses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_referral_links_campaign", "referral_links", ["campaign_id"])
    op.create_index("ix_referral_links_referrer", "referral_links", ["referrer_user_id"])

    op.create_table(
        "campaign_entitlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),  # nth_free | timed_discount | referral_reward
        sa.Column("promocode_id", sa.Integer(), sa.ForeignKey("promocodes.id"), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_campaign_entitlements_user", "campaign_entitlements", ["user_id", "kind"])


def downgrade() -> None:
    op.drop_table("campaign_entitlements")
    op.drop_table("referral_links")
    op.drop_index("ix_wh_deliveries_retry", table_name="company_webhook_deliveries")
    op.drop_index("ix_wh_deliveries_status", table_name="company_webhook_deliveries")
    op.drop_column("company_webhook_deliveries", "next_retry_at")
    op.drop_column("company_webhook_deliveries", "status")
    op.drop_column("company_webhook_deliveries", "max_attempts")
    op.drop_column("company_webhook_deliveries", "attempt")
    op.drop_index("ix_company_members_role_id", table_name="company_members")
    op.drop_column("company_members", "role_id")
    op.drop_index("uq_company_roles_company_slug", table_name="company_roles")
    op.drop_index("ix_company_roles_company_id", table_name="company_roles")
    op.drop_table("company_roles")
