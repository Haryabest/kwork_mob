"""web_fields_faq_tx

Revision ID: 002_web
Revises: 001_initial
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_web"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("staff_role", sa.String(length=30), nullable=True))
    op.add_column(
        "users",
        sa.Column("marketing_opt_in", sa.Boolean(), server_default="true", nullable=False),
    )

    op.create_table(
        "faq_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False, server_default="Общее"),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("tx_type", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])

    op.create_table(
        "support_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("is_staff", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["support_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_messages_request_id", "support_messages", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_support_messages_request_id", table_name="support_messages")
    op.drop_table("support_messages")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("faq_items")
    op.drop_column("users", "marketing_opt_in")
    op.drop_column("users", "staff_role")
    op.drop_column("users", "phone")
