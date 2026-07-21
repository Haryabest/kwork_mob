"""user_events table §12.1"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "044_user_events"
down_revision = "043_upsell_price_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("member_role", sa.String(length=50), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ch_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_events_user_id", "user_events", ["user_id"])
    op.create_index("ix_user_events_company_id", "user_events", ["company_id"])
    op.create_index("ix_user_events_event_type", "user_events", ["event_type"])
    op.create_index("ix_user_events_created_at", "user_events", ["created_at"])
    op.create_index("ix_user_events_ch_synced_at", "user_events", ["ch_synced_at"])


def downgrade() -> None:
    op.drop_index("ix_user_events_ch_synced_at", table_name="user_events")
    op.drop_index("ix_user_events_created_at", table_name="user_events")
    op.drop_index("ix_user_events_event_type", table_name="user_events")
    op.drop_index("ix_user_events_company_id", table_name="user_events")
    op.drop_index("ix_user_events_user_id", table_name="user_events")
    op.drop_table("user_events")
