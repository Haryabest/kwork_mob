"""Миграция: moderation_blacklist §10.8 / §11.

Revision ID: 024_moderation_blacklist
Revises: 023_prefs_campaign_clicks
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024_moderation_blacklist"
down_revision: Union[str, None] = "023_prefs_campaign_clicks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "moderation_blacklist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("word", sa.String(120), nullable=False),
        sa.Column("category", sa.String(32), nullable=False, server_default="general"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_moderation_blacklist_word", "moderation_blacklist", ["word"], unique=True)
    op.execute(
        """
        INSERT INTO moderation_blacklist (word, category, is_active)
        VALUES
          ('оружие', 'product', true),
          ('наркотик', 'product', true),
          ('кокаин', 'product', true),
          ('героин', 'product', true),
          ('порно', 'nsfw', true),
          ('xxx', 'nsfw', true),
          ('weapon', 'product', true),
          ('drugs', 'product', true)
        ON CONFLICT (word) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_moderation_blacklist_word", table_name="moderation_blacklist")
    op.drop_table("moderation_blacklist")
