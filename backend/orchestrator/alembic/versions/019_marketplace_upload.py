"""Миграция: marketplace credentials + upload logs (§7.6 / §14.6).

Revision ID: 019_marketplace_upload
Revises: 018_last_login
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019_marketplace_upload"
down_revision: Union[str, None] = "018_last_login"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketplace_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("marketplace", sa.String(length=10), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_marketplace_credentials_company_id", "marketplace_credentials", ["company_id"])
    op.create_index(
        "uq_marketplace_credentials_scope",
        "marketplace_credentials",
        ["company_id", "marketplace"],
        unique=True,
    )

    op.create_table(
        "marketplace_upload_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_uuid", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("marketplace", sa.String(length=10), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("attempt", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("external_ref", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_marketplace_upload_logs_model_uuid", "marketplace_upload_logs", ["model_uuid"])
    op.create_index("ix_marketplace_upload_logs_company_id", "marketplace_upload_logs", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_marketplace_upload_logs_company_id", table_name="marketplace_upload_logs")
    op.drop_index("ix_marketplace_upload_logs_model_uuid", table_name="marketplace_upload_logs")
    op.drop_table("marketplace_upload_logs")
    op.drop_index("uq_marketplace_credentials_scope", table_name="marketplace_credentials")
    op.drop_index("ix_marketplace_credentials_company_id", table_name="marketplace_credentials")
    op.drop_table("marketplace_credentials")
