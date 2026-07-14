"""Миграция: access_log §10.7.2.

Revision ID: 022_access_log
Revises: 021_support_attachments
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022_access_log"
down_revision: Union[str, None] = "021_support_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "access_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True, index=True),
        sa.Column("model_uuid", sa.String(36), nullable=False, index=True),
        sa.Column("action", sa.String(32), server_default="download", nullable=False),
        sa.Column("file_format", sa.String(10), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_access_log_created_at", "access_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_access_log_created_at", table_name="access_log")
    op.drop_table("access_log")
