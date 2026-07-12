"""shoot_links + photo upload helpers

Revision ID: 006_shoot_links
Revises: 005_workers_pay
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_shoot_links"
down_revision: Union[str, None] = "005_workers_pay"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shoot_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("task_uuid", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="other"),
        sa.Column("tier", sa.String(length=20), nullable=False, server_default="small"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_shoot_links_token", "shoot_links", ["token"], unique=True)
    op.create_index("ix_shoot_links_task_uuid", "shoot_links", ["task_uuid"])


def downgrade() -> None:
    op.drop_index("ix_shoot_links_task_uuid", table_name="shoot_links")
    op.drop_index("ix_shoot_links_token", table_name="shoot_links")
    op.drop_table("shoot_links")
