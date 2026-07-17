"""mobile_analytics_events.ch_synced_at — PG→CH sync cursor §19.20.

Revision ID: 035_analytics_ch_synced_at
Revises: 034_mobile_analytics_events
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "035_analytics_ch_synced_at"
down_revision: Union[str, None] = "034_mobile_analytics_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mobile_analytics_events",
        sa.Column("ch_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_mobile_analytics_events_ch_synced_at",
        "mobile_analytics_events",
        ["ch_synced_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_mobile_analytics_events_ch_synced_at", table_name="mobile_analytics_events")
    op.drop_column("mobile_analytics_events", "ch_synced_at")
