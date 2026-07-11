"""legal consents + support fields

Revision ID: 004_legal_support
Revises: 003_staff_2fa
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_legal_support"
down_revision: Union[str, None] = "003_staff_2fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("support_requests", sa.Column("subject", sa.String(length=255), nullable=True))
    op.add_column("support_requests", sa.Column("category", sa.String(length=50), nullable=True))

    op.create_table(
        "legal_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_documents_slug", "legal_documents", ["slug"])

    op.create_table(
        "user_consents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("document_slug", sa.String(length=50), nullable=False),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_consents_user_id", table_name="user_consents")
    op.drop_table("user_consents")
    op.drop_index("ix_legal_documents_slug", table_name="legal_documents")
    op.drop_table("legal_documents")
    op.drop_column("support_requests", "category")
    op.drop_column("support_requests", "subject")
