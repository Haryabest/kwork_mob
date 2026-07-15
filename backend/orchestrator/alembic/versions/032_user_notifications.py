"""user_notifications inbox §19.16.

Revision ID: 032_user_notifications
Revises: 031_user_inn
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "032_user_notifications"
down_revision: Union[str, None] = "031_user_inn"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dedup_key", sa.String(128), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("model_uuid", sa.String(36), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_user_notifications_user_id", "user_notifications", ["user_id"])
    op.create_index("ix_user_notifications_dedup_key", "user_notifications", ["dedup_key"])
    op.create_index("ix_user_notifications_created_at", "user_notifications", ["created_at"])
    op.create_index(
        "ix_user_notifications_user_dedup",
        "user_notifications",
        ["user_id", "dedup_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_notifications_user_dedup", table_name="user_notifications")
    op.drop_index("ix_user_notifications_created_at", table_name="user_notifications")
    op.drop_index("ix_user_notifications_dedup_key", table_name="user_notifications")
    op.drop_index("ix_user_notifications_user_id", table_name="user_notifications")
    op.drop_table("user_notifications")
