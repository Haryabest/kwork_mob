"""Миграция: model_download_events для воронки §7.9.

Revision ID: 020_publication_funnel
Revises: 019_marketplace_upload
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020_publication_funnel"
down_revision: Union[str, None] = "019_marketplace_upload"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_download_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_uuid", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("file_format", sa.String(length=10), server_default="glb", nullable=False),
        sa.Column("marketplace", sa.String(length=20), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_model_download_events_model_uuid", "model_download_events", ["model_uuid"])
    op.create_index("ix_model_download_events_user_id", "model_download_events", ["user_id"])
    op.create_index("ix_model_download_events_company_id", "model_download_events", ["company_id"])
    op.create_index("ix_model_download_events_created_at", "model_download_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_download_events_created_at", table_name="model_download_events")
    op.drop_index("ix_model_download_events_company_id", table_name="model_download_events")
    op.drop_index("ix_model_download_events_user_id", table_name="model_download_events")
    op.drop_index("ix_model_download_events_model_uuid", table_name="model_download_events")
    op.drop_table("model_download_events")
