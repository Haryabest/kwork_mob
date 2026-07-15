"""balance_pending_payments — YooKassa до webhook §20.3.4.

Revision ID: 033_balance_pending_payments
Revises: 032_user_notifications
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "033_balance_pending_payments"
down_revision: Union[str, None] = "032_user_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "balance_pending_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.String(128), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(30), nullable=False, server_default="redirect"),
        sa.Column("purpose", sa.String(30), nullable=False, server_default="topup"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_balance_pending_payments_payment_id", "balance_pending_payments", ["payment_id"], unique=True)
    op.create_index("ix_balance_pending_payments_user_id", "balance_pending_payments", ["user_id"])
    op.create_index("ix_balance_pending_payments_company_id", "balance_pending_payments", ["company_id"])
    op.create_index("ix_balance_pending_payments_status", "balance_pending_payments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_balance_pending_payments_status", table_name="balance_pending_payments")
    op.drop_index("ix_balance_pending_payments_company_id", table_name="balance_pending_payments")
    op.drop_index("ix_balance_pending_payments_user_id", table_name="balance_pending_payments")
    op.drop_index("ix_balance_pending_payments_payment_id", table_name="balance_pending_payments")
    op.drop_table("balance_pending_payments")
