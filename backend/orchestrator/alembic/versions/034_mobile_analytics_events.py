"""mobile_analytics_events — ingest mobile analytics §19.20.

Revision ID: 034_mobile_analytics_events
Revises: 033_balance_pending_payments
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "034_mobile_analytics_events"
down_revision: Union[str, None] = "033_balance_pending_payments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mobile_analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("event_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("props", JSONB(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mobile_analytics_events_user_id", "mobile_analytics_events", ["user_id"])
    op.create_index("ix_mobile_analytics_events_event", "mobile_analytics_events", ["event"])
    op.create_index("ix_mobile_analytics_events_event_ts", "mobile_analytics_events", ["event_ts"])
    op.create_index("ix_mobile_analytics_events_ingested_at", "mobile_analytics_events", ["ingested_at"])


def downgrade() -> None:
    op.drop_index("ix_mobile_analytics_events_ingested_at", table_name="mobile_analytics_events")
    op.drop_index("ix_mobile_analytics_events_event_ts", table_name="mobile_analytics_events")
    op.drop_index("ix_mobile_analytics_events_event", table_name="mobile_analytics_events")
    op.drop_index("ix_mobile_analytics_events_user_id", table_name="mobile_analytics_events")
    op.drop_table("mobile_analytics_events")
