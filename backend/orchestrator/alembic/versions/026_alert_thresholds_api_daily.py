"""alert thresholds JSONB + api key daily_limit (§12.4.1 / §8.8).

Revision ID: 026_alert_thresholds_api_daily
Revises: 025_segmentation_events
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "026_alert_thresholds_api_daily"
down_revision: Union[str, None] = "025_segmentation_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "alert_settings",
        sa.Column("thresholds", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "company_api_keys",
        sa.Column("daily_limit", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("company_api_keys", "daily_limit")
    op.drop_column("alert_settings", "thresholds")
