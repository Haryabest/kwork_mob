"""user_oauth_identities + nullable users.password_hash.

Revision ID: 036_user_oauth_identities
Revises: 035_analytics_ch_synced_at
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "036_user_oauth_identities"
down_revision: Union[str, None] = "035_analytics_ch_synced_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.create_table(
        "user_oauth_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_user_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )
    op.create_index("ix_user_oauth_identities_user_id", "user_oauth_identities", ["user_id"])
    op.create_index("ix_user_oauth_identities_provider", "user_oauth_identities", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_user_oauth_identities_provider", table_name="user_oauth_identities")
    op.drop_index("ix_user_oauth_identities_user_id", table_name="user_oauth_identities")
    op.drop_table("user_oauth_identities")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
