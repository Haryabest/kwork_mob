"""Миграция: model_feedback (§11.2.4 оценки).

Revision ID: 015_model_feedback
Revises: 014_p1_compliance
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015_model_feedback"
down_revision: Union[str, None] = "014_p1_compliance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_uuid", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_model_feedback_model_uuid", "model_feedback", ["model_uuid"])
    op.create_index("ix_model_feedback_user_id", "model_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_model_feedback_user_id", table_name="model_feedback")
    op.drop_index("ix_model_feedback_model_uuid", table_name="model_feedback")
    op.drop_table("model_feedback")
