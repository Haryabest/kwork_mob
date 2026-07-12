"""company_invitations

Revision ID: 007_company_invites
Revises: 006_shoot_links
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_company_invites"
down_revision: Union[str, None] = "006_shoot_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("inviter_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="photographer"),
        sa.Column("max_concurrent_orders", sa.Integer(), nullable=True),
        sa.Column("monthly_spending_limit", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_company_invitations_token", "company_invitations", ["token"], unique=True)
    op.create_index("ix_company_invitations_email", "company_invitations", ["email"])


def downgrade() -> None:
    op.drop_index("ix_company_invitations_email", table_name="company_invitations")
    op.drop_index("ix_company_invitations_token", table_name="company_invitations")
    op.drop_table("company_invitations")
