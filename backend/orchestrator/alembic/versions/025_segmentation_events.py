"""segmentation_events — метрики fallback/failed по устройству (§11.2.5 / §12.4.1).

Revision ID: 025_segmentation_events
Revises: 024_moderation_blacklist
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025_segmentation_events"
down_revision: Union[str, None] = "024_moderation_blacklist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "segmentation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("device_model", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("os_version", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("failed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("avg_confidence", sa.Float(), nullable=True),
        sa.Column("method", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_segmentation_events_task_id", "segmentation_events", ["task_id"])
    op.create_index("ix_segmentation_events_device_model", "segmentation_events", ["device_model"])
    op.create_index("ix_segmentation_events_os_version", "segmentation_events", ["os_version"])
    op.create_index("ix_segmentation_events_created_at", "segmentation_events", ["created_at"])
    op.add_column("orders", sa.Column("device_model", sa.String(64), nullable=True))
    op.add_column("orders", sa.Column("os_version", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "os_version")
    op.drop_column("orders", "device_model")
    op.drop_index("ix_segmentation_events_created_at", table_name="segmentation_events")
    op.drop_index("ix_segmentation_events_os_version", table_name="segmentation_events")
    op.drop_index("ix_segmentation_events_device_model", table_name="segmentation_events")
    op.drop_index("ix_segmentation_events_task_id", table_name="segmentation_events")
    op.drop_table("segmentation_events")
