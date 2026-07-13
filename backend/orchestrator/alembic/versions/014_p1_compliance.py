"""P1 compliance: SHA-256, deletion requests, finance anonymization.

Revision ID: 014_p1_compliance
Revises: 013_device_tokens
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014_p1_compliance"
down_revision: Union[str, None] = "013_device_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("zip_sha256", sa.String(64), nullable=True))
    op.add_column("orders", sa.Column("customer_name", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("receipt_email", sa.String(255), nullable=True))

    op.add_column("models", sa.Column("file_sha256", sa.String(64), nullable=True))

    op.alter_column("transactions", "user_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("transactions", sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "deletion_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("email_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_by", sa.Integer(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_deletion_requests_status", "deletion_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_deletion_requests_status", table_name="deletion_requests")
    op.drop_table("deletion_requests")
    op.drop_column("transactions", "anonymized_at")
    op.alter_column("transactions", "user_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("models", "file_sha256")
    op.drop_column("orders", "receipt_email")
    op.drop_column("orders", "customer_name")
    op.drop_column("orders", "zip_sha256")
