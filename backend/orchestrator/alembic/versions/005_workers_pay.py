"""workers + payment refs

Revision ID: 005_workers_pay
Revises: 004_legal_support
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_workers_pay"
down_revision: Union[str, None] = "004_legal_support"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="offline"),
        sa.Column("gpu_name", sa.String(length=128), nullable=True),
        sa.Column("gpu_load", sa.Float(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grace_period", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("transactions", sa.Column("external_id", sa.String(length=128), nullable=True))
    op.create_index("ix_transactions_external_id", "transactions", ["external_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_external_id", table_name="transactions")
    op.drop_column("transactions", "external_id")
    op.drop_table("workers")
